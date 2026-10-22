#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>
#include <time.h>
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <X11/Xatom.h>
#include <sys/ipc.h>
#include <sys/shm.h>
#include <X11/extensions/XShm.h>

/*
 * libstealthcloak: Invisible Screen Share Filter for BlockBrain HUD
 *
 * Intercepts X11 screen capture functions (XShmGetImage & XGetImage)
 * in screen sharing clients (Google Chrome / Meet, Discord, Zoom, OBS).
 *
 * When screen capture occurs, it locates the BlockBrain HUD window
 * and replaces its rectangle with the contents of the window directly underneath
 * or background, making the HUD 100% invisible to the screen-share audience!
 */

typedef Status (*XShmGetImage_fn)(Display*, Drawable, XImage*, int, int, unsigned long);
typedef XImage* (*XGetImage_fn)(Display*, Drawable, int, int, unsigned int, unsigned int, unsigned long, int);

static XShmGetImage_fn real_XShmGetImage = NULL;
static XGetImage_fn real_XGetImage = NULL;

static Window cached_hud_window = None;
static time_t last_lookup_time = 0;

static void init_hooks(void) {
    if (!real_XShmGetImage) {
        real_XShmGetImage = (XShmGetImage_fn)dlsym(RTLD_NEXT, "XShmGetImage");
    }
    if (!real_XGetImage) {
        real_XGetImage = (XGetImage_fn)dlsym(RTLD_NEXT, "XGetImage");
    }
}

// Find HUD window recursively by title or property
static Window find_hud_window(Display *d, Window root) {
    Window root_ret, parent_ret;
    Window *children = NULL;
    unsigned int nchildren = 0;
    Window found = None;

    if (!XQueryTree(d, root, &root_ret, &parent_ret, &children, &nchildren) || !children) {
        return None;
    }

    for (int i = (int)nchildren - 1; i >= 0; i--) {
        char *name = NULL;
        if (XFetchName(d, children[i], &name) && name) {
            if (strstr(name, "blockbrain_hud") || strstr(name, "BlockBrain") || strstr(name, "GDR Stealth")) {
                found = children[i];
                XFree(name);
                break;
            }
            XFree(name);
        }
        // Also check WM_CLASS
        XClassHint ch;
        if (XGetClassHint(d, children[i], &ch)) {
            if (ch.res_name && (strstr(ch.res_name, "blockbrain_hud") || strstr(ch.res_name, "blockbrain"))) {
                found = children[i];
            } else if (ch.res_class && (strstr(ch.res_class, "blockbrain_hud") || strstr(ch.res_class, "Blockbrain"))) {
                found = children[i];
            }
            if (ch.res_name) XFree(ch.res_name);
            if (ch.res_class) XFree(ch.res_class);
            if (found != None) break;
        }
    }

    if (children) XFree(children);
    return found;
}

// Find the sibling window directly underneath the HUD window in Z-order
static Window find_window_underneath(Display *d, Window root, Window hud) {
    Window root_ret, parent_ret;
    Window *children = NULL;
    unsigned int nchildren = 0;
    Window under = None;

    if (!XQueryTree(d, root, &root_ret, &parent_ret, &children, &nchildren) || !children) {
        return None;
    }

    int hud_idx = -1;
    for (unsigned int i = 0; i < nchildren; i++) {
        if (children[i] == hud) {
            hud_idx = (int)i;
            break;
        }
    }

    // Look below hud_idx for the first visible mapped window
    if (hud_idx > 0) {
        for (int i = hud_idx - 1; i >= 0; i--) {
            XWindowAttributes attr;
            if (XGetWindowAttributes(d, children[i], &attr)) {
                if (attr.map_state == IsViewable && attr.width > 100 && attr.height > 100) {
                    under = children[i];
                    break;
                }
            }
        }
    }

    if (children) XFree(children);
    return under;
}

// Mask out or blend the HUD window area in the captured image
static void cloak_hud_rect(Display *d, XImage *image, int capture_x, int capture_y) {
    if (!image || !d) return;

    time_t now = time(NULL);
    if (now - last_lookup_time > 1 || cached_hud_window == None) {
        Window root = DefaultRootWindow(d);
        cached_hud_window = find_hud_window(d, root);
        last_lookup_time = now;
    }

    if (cached_hud_window == None) return;

    XWindowAttributes hud_attr;
    if (!XGetWindowAttributes(d, cached_hud_window, &hud_attr)) {
        cached_hud_window = None;
        return;
    }

    if (hud_attr.map_state != IsViewable) return;

    int hud_abs_x = 0, hud_abs_y = 0;
    Window child;
    XTranslateCoordinates(d, cached_hud_window, hud_attr.root, 0, 0, &hud_abs_x, &hud_abs_y, &child);

    // Overlap coordinates between HUD window and captured XImage
    int left = (hud_abs_x > capture_x) ? hud_abs_x : capture_x;
    int top = (hud_abs_y > capture_y) ? hud_abs_y : capture_y;
    int right = (hud_abs_x + hud_attr.width < capture_x + image->width) ? (hud_abs_x + hud_attr.width) : (capture_x + image->width);
    int bottom = (hud_abs_y + hud_attr.height < capture_y + image->height) ? (hud_abs_y + hud_attr.height) : (capture_y + image->height);

    if (left >= right || top >= bottom) return; // No overlap

    // Find window underneath to copy clean background
    Window under = find_window_underneath(d, hud_attr.root, cached_hud_window);
    XImage *under_img = NULL;

    if (under != None) {
        int under_abs_x = 0, under_abs_y = 0;
        XTranslateCoordinates(d, under, hud_attr.root, 0, 0, &under_abs_x, &under_abs_y, &child);
        int src_x = left - under_abs_x;
        int src_y = top - under_abs_y;
        if (src_x >= 0 && src_y >= 0) {
            under_img = real_XGetImage ? real_XGetImage(d, under, src_x, src_y, right - left, bottom - top, AllPlanes, ZPixmap) : NULL;
        }
    }

    for (int y = top; y < bottom; y++) {
        int img_y = y - capture_y;
        for (int x = left; x < right; x++) {
            int img_x = x - capture_x;
            if (under_img) {
                unsigned long px = XGetPixel(under_img, x - left, y - top);
                XPutPixel(image, img_x, img_y, px);
            } else {
                // If no window underneath, blend with the surrounding border pixels seamlessly
                int sample_x = (left > capture_x) ? (left - 1 - capture_x) : ((right < capture_x + image->width) ? (right - capture_x) : img_x);
                int sample_y = (top > capture_y) ? (top - 1 - capture_y) : img_y;
                if (sample_x >= 0 && sample_x < image->width && sample_y >= 0 && sample_y < image->height) {
                    unsigned long bg = XGetPixel(image, sample_x, sample_y);
                    XPutPixel(image, img_x, img_y, bg);
                }
            }
        }
    }

    if (under_img) {
        XDestroyImage(under_img);
    }
}

Status XShmGetImage(Display *d, Drawable dr, XImage *image, int x, int y, unsigned long plane_mask) {
    init_hooks();
    if (!real_XShmGetImage) return 0;

    Status st = real_XShmGetImage(d, dr, image, x, y, plane_mask);
    if (st) {
        cloak_hud_rect(d, image, x, y);
    }
    return st;
}

XImage *XGetImage(Display *d, Drawable dr, int x, int y, unsigned int width, unsigned int height, unsigned long plane_mask, int format) {
    init_hooks();
    if (!real_XGetImage) return NULL;

    XImage *img = real_XGetImage(d, dr, x, y, width, height, plane_mask, format);
    if (img) {
        cloak_hud_rect(d, img, x, y);
    }
    return img;
}
