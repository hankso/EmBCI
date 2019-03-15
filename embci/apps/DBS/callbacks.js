function dataFilter(low, high, notch) {
    if (low == '' || high == '') {
        alert('输入不能为空');
        return;
    }
    low = parseFloat(low).toFixed(1);
    high = parseFloat(high).toFixed(1);
    $.ajax({
        method: 'GET',
        url: 'data/filter',
        data: {
            notch: notch,
            low: low,
            high: high
        },
    })
}

function dataScale(action) {
    $.ajax({
        method: 'GET',
        url: 'data/scale',
        data: {
            scale: action
        },
    })
}

function dataChannel(channel) {
    $.ajax({
        method: "GET",
        url: 'data/channel',
        data: {
            channel: channel
        },
    })
}

function genReport(data, onsuccess) {
    if (data.username == '' || 
        data.gender == '请选择性别' || 
        data.age == '' || 
        data.age < 0 || 
        data.id == '') {
        alert('您填写的数据有误，请检查后重新提交');
        return;
    }
    $.ajax({
        method: 'GET',
        url: 'report',
        data: data,
        success: onsuccess,
    })
}

function dataConfig(data) {
    $.ajax({
        method: 'GET',
        url: 'data/config',
        data: data,
    })
}

var btnCount = 0;
var coefInterval = 0;
var coefBtns = [];

function stateCoef(button) {
    if (!coefBtns.includes(button)) coefBtns.push(button);
    if (button.display) {
        button.display = false;
        $('#' + button.id).css('color', '#333333');
        btnCount--;
    } else {
        button.display = true;
        $('#' + button.id).css('color', '#FFFFFF');
        btnCount++;
    }
    if (btnCount == 0) {
        clearInterval(coefInterval);
        console.log('stop displaying coefs');
        coefInterval = 0;
    } else if (coefInterval == 0) {
        coefInterval = setInterval(dataCoef, 1200);
        console.log('start displaying coefs');
    }
}

function dataCoef() {
    if (!btnCount) return;
    $.ajax({
        method: "GET",
        url: 'data/coef',
        dataType: 'json',
        success: function(msg) {
            updateCoef({
                t: msg.data[0],
                s: msg.data[1],
                m: msg.data[2],
            });
        },
    });
}

function updateCoef(data) {
    for (var i = 0; i < coefBtns.length; i++) {
        var btn = coefBtns[i];
        if (!btn.display) continue;
        var value = data[btn.id[1]] || '0';
        $('#' + btn.id).text(parseFloat(value).toFixed(4));
    }
//    updateRate();
}

function updateRate(before, after, rate) {
    var bef = before.html();
    var aft = after.html();
    if (!isNaN(bef) && !isNaN(aft)) {
        var res = (bef - aft) / bef * 100;
        res = res.toFixed(2);
        rate.html(res + '%');
    }
}