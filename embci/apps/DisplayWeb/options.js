var seriesRaw = [], seriesRawC = [], seriesPwr = [];
var optionRaw = {
    legend: {
        type: 'plain',
        formatter: function(name) {
            return 'CH' + (parseInt(name) + 1);
        },
        selectedMode: 'multiple',
        top: 4,
        itemHeight: 16,
        itemWidth: 20,
        orient: 'horizontal'
    },
    grid: [{
        left: 40,
        right: 40,
        top: 35,
        bottom: 50,
        show: true
    }],
    toolbox: {
        feature: {
            dataZoom: {},
            restore: {},
            saveAsImage: {
                name: 'DBS-Data-Display',
                title: '保存图片',
            },
        },
        itemSize: 14,
        itemGap: 14,
        top: 32,
        right: 10,
        orient: 'vertical'
    },
    xAxis: [{
        position: 'bottom',
        type: 'value',
        name: 'Time / s',
        nameLocation: 'middle',
        nameTextStyle: {
            padding: [10, 0, 0, 0],
        },
        max: xMaxValue,
        min: 0,
        splitLine: {
            show: false
        }
    }],
    yAxis: [{
        gridIndex: 0,
        type: 'value',
        name: 'Channel',
        nameLocation: 'end',
        nameTextStyle: {
            padding: [0, 10, -5, 0],
        },
        max: (v) => Math.max(Math.ceil(v.max), 9),
        min: (v) => Math.min(Math.floor(v.min), 0),
        interval: 1
    }],
    series: seriesRaw,
    // animationDurationUpdate: 1,
};

var optionPwr = {
    legend: {
        type: 'plain',
        formatter: function(name) {
            return 'CH' + (parseInt(name) + 1);
        },
        selectedMode: 'single',
        top: 35,
        right: 10,
        itemGap: 14,
        itemHeight: 14,
        itemWidth: 16,
        orient: 'vertical'
    },
    grid: {
        left: 40,
        right: 70,
        top: 30,
        bottom: 35,
        show: true
    },
    toolbox: {
        feature: {
            myFreqDomain: {},
            dataZoom: {},
            dataView: {},
            restore: {},
            saveAsImage: {
                name: 'DBS-Freq-Display',
                type: 'png'
            },
            magicType: {
                type: ['line', 'bar']
            }
        },
        right: 8
    },
    xAxis: {
        type: 'value',
        name: 'Frequency / Hz',
        nameLocation: 'middle',
        nameTextStyle: {
            padding: 5
        },
        min: 'dataMin',
        max: 'dataMax',
        axisPointer: {
            show: true,
            type: 'line',
        },
    },
    yAxis: {
        type: 'value',
        // name: 'Amplitude / mV',
        name: 'Amplitude',
        nameLocation: 'end',
        nameTextStyle: {
            padding: [0, 0, -5, 20]
        },
        axisPointer: {
            show: true,
            type: 'line',
        },
    },
    series: seriesPwr,
};

var optionRawC = {
    animationEnabled: true,
    exportEnabled: true,
    zoomEnabled: true,
    theme: 'light2',
    // title: {text: 'realtime update'},
    // subtitles: [{text: 'subtitle', fontSize: 15}],
    axisY: {
        title: 'Channel',
        includeZero: false,
        titleFontSize: 24,
    },
    axisX: {
        title: 'Time / s',
        crosshair: {enabled: false, snapToDataPoint: true},
    },
    legend: {
        cursor: 'pointer',
        fontSize: 16,
        horizontalAlign: 'center',
        itemclick: (e) => {
            if (undefined === e.dataSeries.visible) {
                e.dataSeries.visible = true;
            }
            e.dataSeries.visible = !e.dataSeries.visible;
            e.chart.render();
        }
    },
    // toolTip: {shared: true},
    data: seriesRawC,
};

for (var i = 0; i < 8; i++) {
    seriesRaw.push({
        data: [
            // xAxis yAxis
            // [0, Math.random()],
            // [1, Math.random()],
        ],
        // data: nj.stack([nj.random(10), nj.arange(10)], -1).tolist(),
        name: i,
        type: 'line',
        showSymbol: false,
        hoverAnimation: false,
        smooth: false,
        lineStyle: {width: 0.8},
        markLine: {
            animation: false,
            data: [],
            label: {
                formatter: '{event}',
                position: 'end',
            }
        },
        // animationDurationUpdate: 1,
    });
    seriesPwr.push({
        type: 'line',
        data: [],
        name: i,
        xAxisIndex: 0,
        yAxisIndex: 0,
        showSymbol: false,
        smooth: false,
        lineStyle: {
            width: 0.4
        },
        areaStyle: {
            color: '#000',
            opacity: 0,
        },
        sampling: 'average',
        markLine: {
            animation: false,
            data: [
                {
                    xAxis: 50
                },
            ],
            label: {
                formatter: 'Notch',
                position: 'middle',
            }
        },
    });
    seriesRawC.push({
        name: 'CH' + i, type: 'line',
        showInLegend: 'true', dataPoints: []
    });
}

function echartPauseResume(tool, callback) {
    if (!tool.run) {
        tool.icon = 'path://M144 479H48c-26.5 0-48-21.5-48-48V79c0-26.5 21.5-48 48-48h96c26.5 0 48 21.5 48 48v352c0 26.5-21.5 48-48 48zm304-48V79c0-26.5-21.5-48-48-48h-96c-26.5 0-48 21.5-48 48v352c0 26.5 21.5 48 48 48h96c26.5 0 48-21.5 48-48z';
        tool.title = 'Stop';
    } else {
        tool.icon = 'path://M424.4 214.7L72.4 6.6C43.8-10.3 0 6.1 0 47.9V464c0 37.5 40.7 60.1 72.4 41.3l352-208c31.4-18.5 31.5-64.1 0-82.6z';
        tool.title = 'Start';
    }
    callback && callback(tool.run);
    tool.run = !tool.run;
}

var _myFreqDomain = optionPwr.toolbox.feature.myFreqDomain = {
    show: true,
    run: true,
    title: '',
    icon: '',
    onclick: function() {
        echartPauseResume(_myFreqDomain, (currstate) => {
            if (!window.id_interval) window.id_interval = {};
            if (currstate) {
                clearInterval(id_interval['dataFreq']);
            } else {
                dataFreq();
                id_interval['dataFreq'] = setInterval(dataFreq, 1500);
            }
        });
        chartPwr && chartPwr.setOption(optionPwr);
    },
};

_myFreqDomain.onclick();
