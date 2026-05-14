/*
 * Input handling — keyboard, pointer, and keybindings for osa-compositor.
 *
 * Key bindings:
 *   Super+Space  — Toggle AI command palette
 *   Super+Return — Launch terminal (foot)
 *   Super+Q      — Close focused window
 *   Super+F      — Toggle fullscreen
 */

#include <stdlib.h>
#include <unistd.h>
#include <wlr/types/wlr_cursor.h>
#include <wlr/types/wlr_input_device.h>
#include <wlr/types/wlr_keyboard.h>
#include <wlr/types/wlr_pointer.h>
#include <wlr/types/wlr_seat.h>
#include <wlr/types/wlr_xcursor_manager.h>
#include "server.h"

static bool handle_keybinding(struct osa_server *server, xkb_keysym_t sym) {
    switch (sym) {
    case XKB_KEY_space:
        osa_ai_panel_toggle(server);
        return true;
    case XKB_KEY_Return:
        if (fork() == 0) {
            execl("/usr/bin/foot", "foot", NULL);
            _exit(1);
        }
        return true;
    case XKB_KEY_q:
        if (!wl_list_empty(&server->toplevels)) {
            struct osa_toplevel *toplevel =
                wl_container_of(server->toplevels.next, toplevel, link);
            wlr_xdg_toplevel_send_close(toplevel->xdg_toplevel);
        }
        return true;
    case XKB_KEY_f: {
        if (!wl_list_empty(&server->toplevels)) {
            struct osa_toplevel *toplevel =
                wl_container_of(server->toplevels.next, toplevel, link);
            struct wlr_xdg_toplevel *xdg = toplevel->xdg_toplevel;
            wlr_xdg_toplevel_set_fullscreen(xdg, !xdg->current.fullscreen);
        }
        return true;
    }
    case XKB_KEY_Escape:
        wl_display_terminate(server->wl_display);
        return true;
    default:
        return false;
    }
}

static void keyboard_key(struct wl_listener *listener, void *data) {
    struct osa_keyboard *keyboard = wl_container_of(listener, keyboard, key);
    struct osa_server *server = keyboard->server;
    struct wlr_keyboard_key_event *event = data;

    uint32_t keycode = event->keycode + 8;
    const xkb_keysym_t *syms;
    int nsyms = xkb_state_key_get_syms(
        keyboard->wlr_keyboard->xkb_state, keycode, &syms);

    bool handled = false;
    uint32_t modifiers = wlr_keyboard_get_modifiers(keyboard->wlr_keyboard);

    if (event->state == WL_KEYBOARD_KEY_STATE_PRESSED &&
        (modifiers & WLR_MODIFIER_LOGO)) {
        for (int i = 0; i < nsyms; i++) {
            handled = handle_keybinding(server, syms[i]);
            if (handled) break;
        }
    }

    if (!handled) {
        wlr_seat_set_keyboard(server->seat, keyboard->wlr_keyboard);
        wlr_seat_keyboard_notify_key(server->seat,
            event->time_msec, event->keycode, event->state);
    }
}

static void keyboard_modifiers(struct wl_listener *listener, void *data) {
    struct osa_keyboard *keyboard = wl_container_of(listener, keyboard, modifiers);
    wlr_seat_set_keyboard(keyboard->server->seat, keyboard->wlr_keyboard);
    wlr_seat_keyboard_notify_modifiers(keyboard->server->seat,
        &keyboard->wlr_keyboard->modifiers);
}

static void keyboard_destroy(struct wl_listener *listener, void *data) {
    struct osa_keyboard *keyboard = wl_container_of(listener, keyboard, destroy);
    wl_list_remove(&keyboard->modifiers.link);
    wl_list_remove(&keyboard->key.link);
    wl_list_remove(&keyboard->destroy.link);
    wl_list_remove(&keyboard->link);
    free(keyboard);
}

static void new_keyboard(struct osa_server *server, struct wlr_input_device *device) {
    struct wlr_keyboard *wlr_keyboard = wlr_keyboard_from_input_device(device);

    struct osa_keyboard *keyboard = calloc(1, sizeof(*keyboard));
    keyboard->server = server;
    keyboard->wlr_keyboard = wlr_keyboard;

    struct xkb_context *context = xkb_context_new(XKB_CONTEXT_NO_FLAGS);
    struct xkb_keymap *keymap = xkb_keymap_new_from_names(context, NULL,
        XKB_KEYMAP_COMPILE_NO_FLAGS);
    wlr_keyboard_set_keymap(wlr_keyboard, keymap);
    xkb_keymap_unref(keymap);
    xkb_context_unref(context);
    wlr_keyboard_set_repeat_info(wlr_keyboard, 25, 600);

    keyboard->modifiers.notify = keyboard_modifiers;
    wl_signal_add(&wlr_keyboard->events.modifiers, &keyboard->modifiers);

    keyboard->key.notify = keyboard_key;
    wl_signal_add(&wlr_keyboard->events.key, &keyboard->key);

    keyboard->destroy.notify = keyboard_destroy;
    wl_signal_add(&device->events.destroy, &keyboard->destroy);

    wlr_seat_set_keyboard(server->seat, wlr_keyboard);
    wl_list_insert(&server->keyboards, &keyboard->link);
}

static void cursor_motion(struct wl_listener *listener, void *data) {
    struct osa_server *server = wl_container_of(listener, server, cursor_motion);
    struct wlr_pointer_motion_event *event = data;
    wlr_cursor_move(server->cursor, &event->pointer->base, event->delta_x, event->delta_y);
    wlr_cursor_set_xcursor(server->cursor, server->cursor_mgr, "default");
}

static void cursor_motion_absolute(struct wl_listener *listener, void *data) {
    struct osa_server *server = wl_container_of(listener, server, cursor_motion_absolute);
    struct wlr_pointer_motion_absolute_event *event = data;
    wlr_cursor_warp_absolute(server->cursor, &event->pointer->base, event->x, event->y);
    wlr_cursor_set_xcursor(server->cursor, server->cursor_mgr, "default");
}

static void cursor_button(struct wl_listener *listener, void *data) {
    struct osa_server *server = wl_container_of(listener, server, cursor_button);
    struct wlr_pointer_button_event *event = data;
    wlr_seat_pointer_notify_button(server->seat,
        event->time_msec, event->button, event->state);
}

static void cursor_axis(struct wl_listener *listener, void *data) {
    struct osa_server *server = wl_container_of(listener, server, cursor_axis);
    struct wlr_pointer_axis_event *event = data;
    wlr_seat_pointer_notify_axis(server->seat, event->time_msec,
        event->orientation, event->delta, event->delta_discrete,
        event->source, event->relative_direction);
}

static void cursor_frame(struct wl_listener *listener, void *data) {
    struct osa_server *server = wl_container_of(listener, server, cursor_frame);
    wlr_seat_pointer_notify_frame(server->seat);
}

static void new_pointer(struct osa_server *server, struct wlr_input_device *device) {
    wlr_cursor_attach_input_device(server->cursor, device);
}

static void new_input_notify(struct wl_listener *listener, void *data) {
    struct osa_server *server = wl_container_of(listener, server, new_input);
    struct wlr_input_device *device = data;

    switch (device->type) {
    case WLR_INPUT_DEVICE_KEYBOARD:
        new_keyboard(server, device);
        break;
    case WLR_INPUT_DEVICE_POINTER:
        new_pointer(server, device);
        break;
    default:
        break;
    }

    uint32_t caps = WL_SEAT_CAPABILITY_POINTER;
    if (!wl_list_empty(&server->keyboards)) {
        caps |= WL_SEAT_CAPABILITY_KEYBOARD;
    }
    wlr_seat_set_capabilities(server->seat, caps);
}

static void request_cursor_notify(struct wl_listener *listener, void *data) {
    struct osa_server *server = wl_container_of(listener, server, request_cursor);
    struct wlr_seat_pointer_request_set_cursor_event *event = data;
    struct wlr_seat_client *focused = server->seat->pointer_state.focused_client;
    if (focused == event->seat_client) {
        wlr_cursor_set_surface(server->cursor, event->surface,
            event->hotspot_x, event->hotspot_y);
    }
}

static void request_set_selection_notify(struct wl_listener *listener, void *data) {
    struct osa_server *server =
        wl_container_of(listener, server, request_set_selection);
    struct wlr_seat_request_set_selection_event *event = data;
    wlr_seat_set_selection(server->seat, event->source, event->serial);
}

void osa_input_init(struct osa_server *server) {
    server->cursor = wlr_cursor_create();
    wlr_cursor_attach_output_layout(server->cursor, server->output_layout);

    server->cursor_mgr = wlr_xcursor_manager_create(NULL, 24);

    server->cursor_motion.notify = cursor_motion;
    wl_signal_add(&server->cursor->events.motion, &server->cursor_motion);

    server->cursor_motion_absolute.notify = cursor_motion_absolute;
    wl_signal_add(&server->cursor->events.motion_absolute,
        &server->cursor_motion_absolute);

    server->cursor_button.notify = cursor_button;
    wl_signal_add(&server->cursor->events.button, &server->cursor_button);

    server->cursor_axis.notify = cursor_axis;
    wl_signal_add(&server->cursor->events.axis, &server->cursor_axis);

    server->cursor_frame.notify = cursor_frame;
    wl_signal_add(&server->cursor->events.frame, &server->cursor_frame);

    server->seat = wlr_seat_create(server->wl_display, "seat0");

    server->new_input.notify = new_input_notify;
    wl_signal_add(&server->backend->events.new_input, &server->new_input);

    server->request_cursor.notify = request_cursor_notify;
    wl_signal_add(&server->seat->events.request_set_cursor,
        &server->request_cursor);

    server->request_set_selection.notify = request_set_selection_notify;
    wl_signal_add(&server->seat->events.request_set_selection,
        &server->request_set_selection);
}
