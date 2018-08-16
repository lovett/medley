function tick(index, stop) {
    var delay, message;

    delay = 4000;

    if (index >= stop) {
        self.postMessage('finish');
        return;
    }

    self.postMessage('visit:' + index);
    setTimeout(tick, Math.floor(Math.random() * delay) + delay, index + 1, stop);
}

self.addEventListener('message', function (e) {
    var fields, index, stop;
    fields = e.data.split(':');

    if (fields[0] === 'start') {
        index = parseInt(fields[1], 10);
        stop = parseInt(fields[2], 10);
        tick(index, stop);
    }
});
