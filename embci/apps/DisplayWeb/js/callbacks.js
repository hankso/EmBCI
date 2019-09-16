function alertError(e) {
    alert(e.responseText);
}

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

function dataConfig(data) {
    $.ajax({
        method: 'GET',
        url: 'data/config',
        data: data
    })
}

function checkRecordingUser() {
    $.ajax({
        method: 'GET',
        url: 'recorder/username',
        success: function (username) {
            if (username != 'None') {
                $('input#record-user').val(username);
                $('div#recorder').addClass('recording');
            } else {
                $('input#record-user').val('');
                $('div#recorder').removeClass('recording');
            }
        },
    });
}

var channel_pwr = 0, loop_interval = 0;

function loopTask() {
    $.ajax({
        method: 'GET',
        url: 'data/freq',
        dataType: 'json',
        success: function(list) {
            chart_pwr.setOption({
                series: {
                    name: channel_pwr,
                    data: list
                }
            });
        }
    })
}

function echartPause(option) {
    if (!option.toolbox) option.toolbox = {feature: {}};
    if (!option.toolbox.feature.myLoopTask) option.toolbox.feature.myLoopTask = {};
    var f = option.toolbox.feature.myLoopTask;
    if (f.title == '开始') {
        f.icon = 'path://M144 479H48c-26.5 0-48-21.5-48-48V79c0-26.5 21.5-48 48-48h96c26.5 0 48 21.5 48 48v352c0 26.5-21.5 48-48 48zm304-48V79c0-26.5-21.5-48-48-48h-96c-26.5 0-48 21.5-48 48v352c0 26.5 21.5 48 48 48h96c26.5 0 48-21.5 48-48z';
        f.title = '暂停';
        loopTask();
        loop_interval = setInterval(loopTask, 1500);
    } else {
        f.icon = 'path://M424.4 214.7L72.4 6.6C43.8-10.3 0 6.1 0 47.9V464c0 37.5 40.7 60.1 72.4 41.3l352-208c31.4-18.5 31.5-64.1 0-82.6z';
        f.title = '开始';
        clearInterval(loop_interval);
    }
}

var xIndex = 0;
var duration = 1 / 500;
var xMaxValue = 2;
var data = [[], [], [], [], [], [], [], []];


function update2D(arr2d, time) {
    if (!arr2d[0].length) return;
    var ch, len, slice = Math.min(10, arr2d[0].length);
    for (var i = 0; i < slice; i++, xIndex+=duration) {
        if (xIndex >= xMaxValue) {
            xIndex = 0;
//            setTimeout(function(){
            chart_raw.setOption(option_raw);
//            }, 1);
        }
        for (ch = 0; ch < 8; ch++) {
            data[ch].push([xIndex, arr2d[ch].splice(0, 1)[0] + ch + 1]);
        }
    }
    for (ch = 0; ch < 8; ch++) {
        chart_raw.appendData({
            seriesIndex: ch,
            data: data[ch]
        });
        data[ch].length = 0;
    }
    setTimeout(function() {
        update2D(arr2d, time)
    }, time);
}
