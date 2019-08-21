function visit(index, limit) {
    const minDelay = 4000;
    const maxDelay = 8000;

    if (index > limit) {
        self.postMessage('finish');
        self.close();
        return;
    }

    self.postMessage('visit:' + index);

    setTimeout(
        visit,
        Math.random() * (maxDelay - minDelay) + minDelay,
        index + 1,
        limit
    );
}

self.addEventListener('message', function (e) {
    const fields = e.data.split(':');

    if (fields[0] === 'start') {
        const limit = parseInt(fields[1], 10);
        const offset = parseInt(fields[2], 10);
        visit(offset, offset + limit - 1);
    }
});
