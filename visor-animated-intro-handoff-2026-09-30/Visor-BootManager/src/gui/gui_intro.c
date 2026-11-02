#include "gui_internal.h"

static void intro_paint(gui_state_t *state, icon_t *image, UINTN alpha) {
    UINTN width = state->screen_width;
    UINTN height = state->screen_height;
    UINTN draw_width = width;
    UINTN draw_height = (UINT64)image->height * width / image->width;
    if (draw_height > height) {
        draw_height = height;
        draw_width = (UINT64)image->width * height / image->height;
    }
    if (!draw_width || !draw_height) return;
    UINTN left = (width - draw_width) / 2;
    UINTN top = (height - draw_height) / 2;
    for (UINTN pixel = 0; pixel < width * height; pixel++)
        state->backbuffer[pixel] = 0xFF000000u;
    for (UINTN row = 0; row < draw_height; row++) {
        UINTN source_row = (UINT64)row * image->height / draw_height;
        for (UINTN column = 0; column < draw_width; column++) {
            UINTN source_column = (UINT64)column * image->width / draw_width;
            UINT32 color = image->pixels[source_row * image->width + source_column];
            UINTN opacity = ((color >> 24) * alpha) / 255;
            UINT32 red = ((color >> 16) & 255) * opacity / 255;
            UINT32 green = ((color >> 8) & 255) * opacity / 255;
            UINT32 blue = (color & 255) * opacity / 255;
            state->backbuffer[(top + row) * width + left + column] =
                0xFF000000u | (red << 16) | (green << 8) | blue;
        }
    }
    UINTN title_size = clamp_uintn(height / 16, 20, 72);
    UINTN hint_size = clamp_uintn(height / 48, 12, 24);
    UINTN padding = hint_size / 2;
    UINTN title_y = height / 12;
    UINTN hint_y = height * 9 / 10;
    fill_rect_alpha(state, width / 12 - padding, title_y - padding,
                    text_width_px(L"VISOR", title_size) + padding * 2,
                    title_size + padding * 2, COLOR_BLACK, alpha * 220 / 255);
    fill_rect_alpha(state, width / 12 - padding, hint_y - padding,
                    text_width_px(L"Press any key to continue", hint_size) + padding * 2,
                    hint_size + padding * 2, COLOR_BLACK, alpha * 220 / 255);
    draw_text_px(state, L"VISOR", width / 12, title_y,
                 (color_t){alpha, alpha, alpha}, title_size);
    draw_text_px(state, L"Press any key to continue", width / 12, hint_y,
                 (color_t){alpha * 150 / 255, alpha * 190 / 255, alpha * 220 / 255},
                 hint_size);
    gui_present(state);
}

int gui_show_intro(gui_state_t *state, CHAR16 *path, UINTN duration_ms,
                   int loop, int auto_continue) {
    if (!state || !state->backbuffer || !state->screen_width ||
        !state->screen_height || !path || !path[0] || !duration_ms)
        return 0;
    if (duration_ms > 5000) duration_ms = 5000;
    anim_t *animation = NULL;
    icon_t canvas = {0};
    icon_t *image = NULL;
    if (path_anim_kind(path)) {
        animation = gui_load_anim(path, NULL, state->screen_width, state->screen_height);
        if (!animation) return 0;
        animation->loops = 0;
        canvas.width = animation->width;
        canvas.height = animation->height;
        canvas.pixels = animation->canvas;
        image = &canvas;
    } else {
        image = gui_load_image(path);
        if (!image) return 0;
    }
    int result = INTRO_BYPASSED;
    EFI_EVENT deadline = NULL;
    if (!image->pixels || !image->width || !image->height) goto cleanup;
    if (auto_continue) {
        if (EFI_ERROR(BS->CreateEvent(EVT_TIMER, TPL_CALLBACK, NULL, NULL, &deadline)))
            goto cleanup;
        if (EFI_ERROR(BS->SetTimer(deadline, TimerRelative, (UINT64)duration_ms * 10000)))
            goto cleanup;
    }
    arch_clock_init();
    UINT64 start = arch_now_us();
    UINTN last_alpha = 256;
    UINT64 next_frame_us = animation ? (UINT64)(animation->cur_delay ? animation->cur_delay : 10) * 1000 : 0;
    int playing = animation && state->animation;
    for (;;) {
        EFI_INPUT_KEY key;
        if (!EFI_ERROR(ST->ConIn->ReadKeyStroke(ST->ConIn, &key))) {
            result = INTRO_SKIPPED;
            break;
        }
        if (deadline) {
            EFI_STATUS status = BS->CheckEvent(deadline);
            if (status == EFI_SUCCESS) { result = INTRO_FINISHED; break; }
            if (status != EFI_NOT_READY) break;
        }
        UINT64 elapsed = arch_now_us() - start;
        int frame_changed = 0;
        if (playing && elapsed >= next_frame_us) {
            if (!loop && animation->cur >= animation->frame_count - 1) {
                playing = 0;
                if (auto_continue) { result = INTRO_FINISHED; break; }
            } else if (!anim_advance_n(animation, 1)) {
                break;
            } else {
                canvas.pixels = animation->canvas;
                frame_changed = 1;
                next_frame_us = elapsed + (UINT64)(animation->cur_delay ? animation->cur_delay : 10) * 1000;
            }
        }
        UINTN fade_us = duration_ms < 500 ? duration_ms * 500 : 250000;
        UINTN alpha = (!gui_animation_on(state) || elapsed >= fade_us) ? 255
                    : (UINTN)(elapsed * 255 / fade_us);
        if (alpha != last_alpha || frame_changed) {
            intro_paint(state, image, alpha);
            last_alpha = alpha;
        }
        if (state->sound_poll) state->sound_poll();
        BS->Stall(16000);
    }
cleanup:
    if (deadline) BS->CloseEvent(deadline);
    if (animation) {
        anim_free(animation);
    } else {
        if (image->scaled) efi_free_pool(image->scaled);
        if (image->pixels) efi_free_pool(image->pixels);
        efi_free_pool(image);
    }
    return result;
}
