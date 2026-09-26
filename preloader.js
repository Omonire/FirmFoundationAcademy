/* ============================================================
   PRELOADER
   Holds the splash screen until the page is genuinely ready:
     1. header.html + footer.html fetched and injected
     2. Lucide CDN loaded and icons rendered
     3. Webfonts loaded (document.fonts.ready)
     4. Above-the-fold images decoded
   A hard timeout guarantees the splash can never trap the user.
   ============================================================ */
(function () {
    'use strict';

    var HARD_TIMEOUT = 10000;   // never trap the user behind the splash
    var MIN_VISIBLE  = 350;     // avoid a 1-frame flash on fast loads

    var splash   = document.getElementById('splash');
    var bar      = document.getElementById('splash-bar');
    var statusEl = document.getElementById('splash-status');
    var started  = Date.now();
    var finished = false;
    var progress = 0;
    var tasks    = [];

    // Reveal content even if JS dies later (e.g. CDN blocked).
    // Set as early as possible so there is never an invisible page.
    document.documentElement.classList.add('js');

    function setProgress(p, label) {
        progress = Math.max(progress, p);
        if (bar) bar.style.width = Math.min(100, progress) + '%';
        if (statusEl && label) statusEl.textContent = label;
    }

    function finish() {
        if (finished) return;
        finished = true;

        // make sure everything is revealed even if a task silently failed
        document.querySelectorAll('.reveal').forEach(function (el) {
            el.classList.add('active');
        });

        if (bar) bar.style.width = '100%';
        if (statusEl) statusEl.textContent = 'Ready';

        var elapsed = Date.now() - started;
        var wait = Math.max(0, MIN_VISIBLE - elapsed);

        setTimeout(function () {
            if (splash) splash.classList.add('splash-done');
            // remove from the a11y tree + hit-testing once faded
            setTimeout(function () {
                if (splash && splash.parentNode) splash.parentNode.removeChild(splash);
            }, 500);
            document.body.classList.add('is-ready');
        }, wait);
    }

    // ---- individual readiness checks -------------------------------

    function fontsReady() {
        if (!document.fonts || !document.fonts.ready) return Promise.resolve();
        // Loading fonts can hang if Google Fonts is blocked; race a timeout.
        return Promise.race([
            document.fonts.ready,
            new Promise(function (r) { setTimeout(r, 4000); })
        ]);
    }

    function lucideReady() {
        if (typeof window.lucide !== 'undefined' && window.lucide.createIcons) {
            try { window.lucide.createIcons(); } catch (e) { /* non-fatal */ }
            return Promise.resolve();
        }
        // script may still be in flight
        return new Promise(function (resolve) {
            var waited = 0;
            var iv = setInterval(function () {
                if (typeof window.lucide !== 'undefined' && window.lucide.createIcons) {
                    clearInterval(iv);
                    try { window.lucide.createIcons(); } catch (e) { /* non-fatal */ }
                    resolve();
                } else if ((waited += 100) > 4000) {
                    clearInterval(iv);
                    resolve();
                }
            }, 100);
        });
    }

    function aboveFoldImagesReady() {
        var vh = window.innerHeight || 800;
        var imgs = Array.prototype.slice
            .call(document.querySelectorAll('img'))
            .filter(function (img) {
                if (img.loading === 'lazy') return false;
                var r = img.getBoundingClientRect();
                return r.top < vh * 1.5 && r.bottom > -200;   // near viewport
            });

        if (!imgs.length) return Promise.resolve();

        var waits = imgs.map(function (img) {
            if (img.complete && img.naturalWidth > 0) return Promise.resolve();
            return new Promise(function (resolve) {
                var done = false;
                var finish = function () {
                    if (done) return;
                    done = true;
                    img.removeEventListener('load', finish);
                    img.removeEventListener('error', finish);
                    resolve();
                };
                img.addEventListener('load', finish);
                img.addEventListener('error', finish);
                setTimeout(finish, 5000);   // never block on one bad URL
            });
        });
        return Promise.all(waits);
    }

    function stylesheetsReady() {
        var sheets = Array.prototype.slice.call(document.styleSheets);
        var waits = sheets.map(function (sheet) {
            if (!sheet.href) return Promise.resolve();          // inline <style>
            if (sheet.__done) return Promise.resolve();
            return new Promise(function (resolve) {
                var done = false;
                var finish = function () {
                    if (done) return;
                    done = true;
                    sheet.__done = true;
                    resolve();
                };
                sheet.addEventListener('load', finish);
                sheet.addEventListener('error', finish);
                // link may already be complete before we attached
                try {
                    var rules = sheet.cssRules;
                    if (rules) { sheet.__done = true; resolve(); return; }
                } catch (e) { /* cross-origin sheet: rely on load event */ }
                setTimeout(finish, 5000);
            });
        });
        return Promise.all(waits);
    }

    // ---- run them in ordered phases so the progress bar is honest --

    var phases = [
        { p: 20, label: 'Loading styles\u2026', run: stylesheetsReady },
        { p: 40, label: 'Loading fonts\u2026',   run: fontsReady },
        { p: 60, label: 'Loading icons\u2026',   run: lucideReady },
        { p: 80, label: 'Loading images\u2026',  run: aboveFoldImagesReady },
        { p: 95, label: 'Almost there\u2026',    run: function () { return Promise.resolve(); } }
    ];

    function runPhases(i) {
        if (i >= phases.length) { finish(); return; }
        var ph = phases[i];
        setProgress(ph.p, ph.label);
        var r;
        try { r = ph.run(); } catch (e) { r = Promise.resolve(); }
        Promise.resolve(r).then(function () {
            runPhases(i + 1);
        }, function () {
            runPhases(i + 1);   // a failed phase must not block the page
        });
    }

    // ---- wait for the page's own loadIncludes() if it has one -------

    function includesReady() {
        // pages call loadIncludes() on DOMContentLoaded; wait for the
        // header/footer placeholders to actually contain markup
        var hp = document.getElementById('header-placeholder');
        if (!hp) return Promise.resolve();

        return new Promise(function (resolve) {
            var waited = 0;
            var iv = setInterval(function () {
                if (hp.innerHTML.trim().length > 0) {
                    clearInterval(iv);
                    resolve();
                } else if ((waited += 80) > 5000) {
                    clearInterval(iv);
                    resolve();   // header fetch failed; show page anyway
                }
            }, 80);
        });
    }

    function start() {
        includesReady().then(function () {
            runPhases(0);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', start);
    } else {
        start();
    }

    // absolute failsafe
    setTimeout(finish, HARD_TIMEOUT);

    // re-render lucide + re-check after a client-side nav, if any
    document.addEventListener('astro:page-load', function () {
        if (window.lucide && window.lucide.createIcons) {
            try { window.lucide.createIcons(); } catch (e) { /* non-fatal */ }
        }
    });
})();
