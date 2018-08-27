function tick(index, limit) {
    var delay, message;

    delay = 4000;

    if (index > limit) {
        self.postMessage('finish');
        return;
    }

    self.postMessage('visit:' + index);
    setTimeout(tick, Math.floor(Math.random() * delay) + delay, index + 1, limit);
}

self.addEventListener('message', function (e) {
    let fields = e.data.split(':');

    if (fields[0] === 'start') {
        let limit = parseInt(fields[1], 10);
        let offset = parseInt(fields[2], 10);
        tick(offset, offset + limit - 1);
    }
});
