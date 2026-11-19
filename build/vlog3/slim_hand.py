"""Kuruskan tangan (pengguna) pada 2 gambar cincin: local warp that pulls the hand's sides toward its axis.
Only a soft region around the hand moves; everything else is untouched. Output 2160x3840 (9:16) JPEGs."""
import cv2, numpy as np, sys
W, H = 2160, 3840
JOBS = {   # name: (centre (x,y) as fraction, axis start->end fractions (wrist -> fingers), half-width px, k)
    'IMG_0792': ((0.47, 0.58), (0.62, 0.72), (0.33, 0.45), 430, 0.90, 'mask'),
    'IMG_0793': ((0.50, 0.67), (0.20, 0.90), (0.62, 0.45), 560, 0.92, 'warp'),
}
def smooth(x0, x1, v):   # 1 below x0, 0 above x1
    t = np.clip((v - x0) / (x1 - x0), 0, 1); return 1 - t * t * (3 - 2 * t)
for name, (c, a, b, half, k, mode) in JOBS.items():
    img = cv2.resize(cv2.imread(f'rakaman/vlog3/{name}.jpeg'), (W, H), interpolation=cv2.INTER_AREA)
    cx, cy = c[0] * W, c[1] * H
    u = np.array([(b[0] - a[0]) * W, (b[1] - a[1]) * H]); L = np.linalg.norm(u); u /= L; n = np.array([-u[1], u[0]])
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    px, py = xs - cx, ys - cy
    d = px * n[0] + py * n[1]                 # signed distance from the hand axis
    al = px * u[0] + py * u[1]                # position along the axis
    w = (smooth(half * 1.1, half * 2.0, np.abs(d)) if mode == 'mask' else smooth(half * 0.9, half * 1.45, np.abs(d))) * smooth(L * 0.75, L * 1.05, np.abs(al))
    s = d * (1 / k - 1) * w                   # sample farther out -> sides drawn inward
    mx = (xs + n[0] * s).astype(np.float32); my = (ys + n[1] * s).astype(np.float32)
    warped = cv2.remap(img, mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    # keep the background straight: only the hand (skin + rings, the blob at the hand centre) is taken from the warp;
    # the strip the hand no longer covers is filled from the surrounding background (inpaint)
    if mode == 'warp':
        out = warped; hand = hand_w = gap = np.zeros((H, W), np.uint8)
    else:
        # hand mask by GrabCut with a shape prior (colour alone fails: the cream/gold wall is skin-coloured)
        sc = 4; sm = cv2.resize(img, (W // sc, H // sc)); dd = cv2.resize(np.abs(d), (W // sc, H // sc)); aa = cv2.resize(np.abs(al), (W // sc, H // sc))
        gm = np.full(dd.shape, cv2.GC_BGD, np.uint8)
        gm[(dd < half * 2.2) & (aa < L * 1.15)] = cv2.GC_PR_BGD
        gm[(dd < half * 1.15) & (aa < L * 0.95)] = cv2.GC_PR_FGD
        gm[(dd < half * 0.45) & (aa < L * 0.6)] = cv2.GC_FGD
        bgm, fgm = np.zeros((1, 65)), np.zeros((1, 65))
        cv2.grabCut(sm, gm, None, bgm, fgm, 6, cv2.GC_INIT_WITH_MASK)
        hs = np.where((gm == cv2.GC_FGD) | (gm == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
        hs = cv2.morphologyEx(hs, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        num, lab = cv2.connectedComponents(hs)
        hs = ((lab == lab[int(cy) // sc, int(cx) // sc]) * 255).astype(np.uint8)
        hand = cv2.GaussianBlur(cv2.resize(hs, (W, H), interpolation=cv2.INTER_CUBIC), (21, 21), 0); hand = ((hand > 127) * 255).astype(np.uint8)   # smooth edge, no staircase
        hand[(np.abs(d) > half * 1.35) | (np.abs(al) > L * 1.05)] = 0   # never take background far from the hand
        cnts, _ = cv2.findContours(hand, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        hand = np.zeros_like(hand); cv2.drawContours(hand, cnts, -1, 255, -1)          # fill holes (rings)
        hand_w = cv2.remap(hand, mx, my, cv2.INTER_LINEAR)
        gap = cv2.dilate(cv2.bitwise_and(hand, cv2.bitwise_not(cv2.erode(hand_w, np.ones((5, 5), np.uint8)))), np.ones((15, 15), np.uint8))
        small = cv2.resize(img, (W // 4, H // 4)); gs = cv2.resize(cv2.dilate(hand, np.ones((41, 41), np.uint8)), (W // 4, H // 4))   # inpaint from background only (no skin bleeding into the strip)
        bg = cv2.resize(cv2.inpaint(small, gs, 9, cv2.INPAINT_TELEA), (W, H), interpolation=cv2.INTER_CUBIC)
        base = img.copy(); g3 = (cv2.GaussianBlur(gap, (31, 31), 0) / 255.0)[..., None]
        base = (base * (1 - g3) + bg * g3).astype(np.uint8)
        a3 = (cv2.GaussianBlur(cv2.erode(hand_w, np.ones((5, 5), np.uint8)), (7, 7), 0) / 255.0)[..., None]
        out = (warped * a3 + base * (1 - a3)).astype(np.uint8)
    cv2.imwrite(sys.argv[1] + f'/{name}_mask.jpg', cv2.resize(np.hstack([hand, hand_w, gap]), (540, 320)))
    cv2.imwrite(f'build/vlog3/{name}_slim.jpg', out, [cv2.IMWRITE_JPEG_QUALITY, 95])
    side = np.hstack([cv2.resize(img, (360, 640)), cv2.resize(out, (360, 640))])
    cv2.imwrite(sys.argv[1] + f'/{name}_cmp.jpg', side)
    print(name, 'ok')
