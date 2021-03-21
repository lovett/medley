MEDLEY.recipes = (function () {
    function pasteCleanup(field) {
        const pairs = [
            [/½/g, "1/2"],
            [/⅓/g, "1/3"],
            [/⅔/g, "2/3"],
            [/¼/g, "1/4"],
            [/¾/g, "3/4"],
            [/⅕/g, "1/5"],
            [/⅖/g, "2/5"],
            [/⅗/g, "3/5"],
            [/⅘/g, "4/5"],
            [/⅙/g, "1/6"],
            [/⅚/g, "5/6"],
            [/⅐/g, "1/7"],
            [/⅛/g, "1/8"],
            [/⅜/g, "3/8"],
            [/⅝/g, "5/8"],
            [/⅞/g, "7/8"],
            [/⅑/g, "1/9"],
            [/⅒/g, "1/10"],
            [/\s*°\s*F?/g, "F"]
        ];

        pairs.forEach((pair) => {
            field.value = field.value.replace(
                pair[0], pair[1]
            );
        });
    }

    function toggleStrike(e) {
        if (e.target.closest('section') === null) {
            return;
        }

        if (e.target.nodeName === 'P' || e.target.nodeName === 'LI') {
            e.target.classList.toggle('done');
        }
    }

    return {
        init: function () {
            if (document.getElementById('recipe')) {
                document.addEventListener(
                    'click',
                    toggleStrike
                );
            }

            let target = document.querySelector('textarea[name=body]');
            if (target) {
                target.addEventListener(
                    'paste',
                    (e) => {
                        setTimeout(function () {
                            pasteCleanup(e.target);
                        }, 250);
                    }
                );
            }

            target = document.querySelector('#tagset A');
            if (target) {
                MEDLEY.focusAsYouType('#tagset A, #collection A');
            }
        }
    }
})();

window.addEventListener('DOMContentLoaded',  MEDLEY.recipes.init);
