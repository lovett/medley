MEDLEY.clipboard = (function () {

    function copyToClipboard(e) {
        if (!e.target.classList.contains('clipboard')) {
            return;
        }

        e.preventDefault();


        const surrogate = e.target.closest('.clipboard-button').getElementsByTagName('TEXTAREA')[0];

        const copyId = e.target.dataset.targetId;
        if (copyId) {
            const target = document.getElementById(copyId);
            surrogate.value = target.innerHTML;
        }

        surrogate.select();
        document.execCommand('copy');
        e.target.classList.add('clicked');
        setTimeout(() => e.target.classList.remove('clicked'), 1000);

    }

    return {
        init: function () {
            document.addEventListener('click', copyToClipboard);
        }
    }
})();

window.addEventListener('DOMContentLoaded',  MEDLEY.clipboard.init);
