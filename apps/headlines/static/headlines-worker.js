function visit(start, stop) {
    const minDelay = 4000;
    const maxDelay = 8000;

    const firstIndex = start - 1;
    const lastIndex = stop - 1;

    if (firstIndex > lastIndex) {
        self.postMessage('finish');
        self.close();
        return;
    }

    self.postMessage('visit:' + firstIndex);

    setTimeout(
        visit,
        Math.random() * (maxDelay - minDelay) + minDelay,
        start + 1,
        stop
    );
}

self.addEventListener('message', function (e) {
    const fields = e.data.split(':');
    const start = parseInt(fields[0], 10);
    const stop = parseInt(fields[1], 10);
    visit(start, stop);
});
