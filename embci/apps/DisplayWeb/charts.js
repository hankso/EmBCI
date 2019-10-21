function _oneTimeInit() {
    setTimeout(() => {
        // $(window).trigger('resize');
        window.dispatchEvent(new Event('resize'));
    }, 100);
    pECT = {}, pCVS = {};
    return _oneTimeInit;
}

function initRaw() {
    chartRaw = echarts.init($('#chart-raw')[0], 'macarons', {
        // width: $('#chart-raw').css('width'),
        height: 35 + 50 + 8 * 60
    });
    chartRaw.setOption(optionRaw);
    chartRaw.on('legendselectchanged', msg => {
        dataChannel({
            channel: msg.name,
            action: msg.selected[msg.name]
        });
    });
    window.addEventListener("resize", chartRaw.resize);
    initRaw = _oneTimeInit();
}

function initRawC() {
    chartRawC = $('#chart-cvs')
        //.css('width', width)
        .css('height', 35 + 50 + 8 * 60)
        .CanvasJSChart(optionRawC).CanvasJSChart();
    CanvasJS.Chart.prototype.clear = function() {
        for (let i = 0; i < this.options.data.length; i++) {
            this.options.data[i].dataPoints.length = 0;
        }
        this.setOptions(this.options);
    };
    window.addEventListener("resize", chartRawC.windowResizeHandler);
    // TODO: add legend selection callback
    initRawC = _oneTimeInit();
}

function initPwr() {
    chartPwr = echarts.init($('#chart-pwr')[0], 'macarons', {
        // width: $('#chart-pwr').css('width'),
        height: 30 + 35 + 210
    });
    chartPwr.setOption(optionPwr);
    chartPwr.on('legendselectchanged', msg => {
        var selected = chartRaw.getOption().legend[0].selected;
        channelPwr = msg.name;
        if (undefined == selected[msg.name]) {
            // Enable channel
            dataChannel({channel: msg.name, action: true});
        } else {
            // Change to this channel
            dataChannel({channel: msg.name});
        }
    });
    window.addEventListener("resize", chartPwr.resize);
    initPwr = _oneTimeInit();
}

var pECT = {}, pCVS = {};

function update2DEcharts(arr2d, time) {
    if (!arr2d[0].length) {
        return numPack--; //console.log('End', numPack, Date.now());
    } else setTimeout(() => update2DEcharts(arr2d, time), time);
    if (undefined === pECT.buffer) {  // first call
        pECT.buffer = [[], [], [], [], [], [], [], []];
        pECT.max = xMaxValue;
        pECT.x = 0;
    }
    var i, ch, len = Math.min(10, arr2d[0].length);
    for (i = 0; i < len; i++, pECT.x += duration) {
        if (pECT.x >= pECT.max) {
            pECT.x = 0;
            for (ch = 0; ch < 8; ch++) seriesRaw[ch].data.length = 0;
            chartRaw.setOption(optionRaw);
            // setTimeout(() => chartRaw.setOption(optionRaw), 1);
        }
        for (ch = 0; ch < 8; ch++) {
            pECT.buffer[ch].push([pECT.x, arr2d[ch].shift() + ch + 1]);
        }
    }
    // console.time('chartAppend');
    for (ch = 0; ch < 8; ch++) {
        /*
        seriesRaw[ch].data = nj.stack([
            pECT.indexs, nj.array(pECT.buffer[ch]).add(ch + 1)
        ], -1).tolist();
        */
        chartRaw.appendData({
            seriesIndex: ch,
            data: pECT.buffer[ch]
        });
        pECT.buffer[ch].length = 0;
    }
    // console.timeEnd('chartAppend');
}

function scroll2DCanvas(arr2d, time=50) {
    if (!arr2d[0].length) {
        return numPack--; //console.log('End', numPack, Date.now());
    }
    else setTimeout(() => scroll2DCanvas(arr2d, time), time);
    if (undefined === pCVS.buffer) {  // first call
        pCVS.max = xMaxValue;
        pCVS.pts = pCVS.max * sampleRate;
        pCVS.indexs = nj.arange(0, pCVS.pts).divide(sampleRate);
        pCVS.buffer = nj.zeros([8, pCVS.pts]).tolist();
    }
    // var i, ch, len = Math.min(25, arr2d[0].length);
    var i, ch, len = arr2d[0].length;
    for (ch = 0; ch < 8; ch++) {
        pCVS.buffer[ch] = pCVS.buffer[ch].slice(len).concat(arr2d[ch].splice(0, len));
        for (i = 0; i < pCVS.pts; i++) {
            if (seriesRawC[ch].dataPoints.length <= i) {
                seriesRawC[ch].dataPoints.push({
                    x: pCVS.indexs[i], y: pCVS.buffer[ch][i] + ch + 1
                });
            } else {
                seriesRawC[ch].dataPoints[i].y = pCVS.buffer[ch][i] + ch + 1;
            }
        }
    }
    // console.time('chartScroll');
    chartRawC.render();
    // console.timeEnd('chartScroll');
}
