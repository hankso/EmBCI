function dataFilter(low, high, notch) {
    var data = {};
    if (low != undefined && high != undefined) {
        data.low = parseFloat(low);
        data.high = parseFloat(high);
    }
    if (notch != undefined) {
        data.notch = notch;
    }
    $.ajax({
        method: 'GET',
        url: 'data/filter',
        data: data
    })
}

function dataScale(action) {
    $.ajax({
        method: 'GET',
        url: 'data/scale',
        dataType: 'json',
        data: {
            scale: action
        },
        success: function(obj) {
            var scale = obj.a[obj.i];
            if (parseFloat(scale) != NaN) {
                $('#scale-text').text(scale + 'x');
            } else {
                $('#scale-text').text('E');
                console.error('scale: ', scale);
            }
        }
    });
}

function dataChannel(opt) {
    $.ajax({
        method: "GET",
        url: 'data/channel',
        data: opt
    })
}

function dataFreq() {
    $.ajax({
        method: 'GET',
        url: 'data/freq',
        dataType: 'json',
        success: function(list) {
            // var selected = chartPwr.getOption().legend[0].selected;
            // channel_pwr = Object.values(selected).indexOf(true);
            chartPwr.setOption({
                series: {
                    name: channel_pwr,
                    data: list
                }
            });
        }
    })
}

function dataConfig(data) {
    $.ajax({
        method: 'GET',
        url: 'data/config',
        data: data
    })
}

function recorderCallback(event, param) {
    var cmd = ('string' === typeof event) ? event : event.type;
    var success = ('function' === typeof param) ? param : () => {};
    $.ajax({
        method: 'GET',
        url: 'recorder/' + cmd,
        success: success,
        error: msg => console.error(msg)
    });
}
