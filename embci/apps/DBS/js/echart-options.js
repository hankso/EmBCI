var colors = ['#c23531','#2f4554', '#61a0a8', '#d48265', '#91c7ae','#749f83',  '#ca8622', '#bda29a','#6e7074', '#546570', '#c4ccd3'];
var nowColor = colors[0];

var n_interval;

function echartPause(option) {
    var f = option.toolbox.feature.myPauseAndResume;
    if (f.title == '开始') {
        f.icon = 'path://M144 479H48c-26.5 0-48-21.5-48-48V79c0-26.5 21.5-48 48-48h96c26.5 0 48 21.5 48 48v352c0 26.5-21.5 48-48 48zm304-48V79c0-26.5-21.5-48-48-48h-96c-26.5 0-48 21.5-48 48v352c0 26.5 21.5 48 48 48h96c26.5 0 48-21.5 48-48z';
        f.title = '暂停';
        n_interval = setInterval(loopTask, 1500);
    } else {
        f.icon = 'path://M424.4 214.7L72.4 6.6C43.8-10.3 0 6.1 0 47.9V464c0 37.5 40.7 60.1 72.4 41.3l352-208c31.4-18.5 31.5-64.1 0-82.6z';
        f.title = '开始';
        clearInterval(n_interval);
    }
}

var option_raw = {
    legend: {
        type: 'plain',
        orient: 'horizontal',
        top: 4,
        itemHeight: 16,
        //right: 40,
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
            dataView: {},
            restore: {},
            saveAsImage: {
                name: 'DBS-Data-Display',
                title: '保存图片',
            },
        },
        itemSize: 14,
        itemGap: 14,
        top: 32,
        right: 8,
        orient: 'vertical'
    },
    xAxis: [{
        position: 'bottom',
        type: 'value',
        name: 'Time / s',
        nameLocation: 'middle',
        max: 1,
        min: 0,
        splitLine: {
            show: false
        }
    }],
    yAxis: [{
        gridIndex: 0,
        type: 'value',
        name: 'Voltage / V',
        nameLocation: 'end',
        nameTextStyle: {
            padding: [0, 15, -5, 0],
        },
        max: 9, 
//        max: (v) => Math.min(Math.ceil(v.max), 9),
        min: 0,
//        min: (v) => Math.floor(v.min),
        interval: 1
    }],
    series: [],
    animationDurationUpdate: 1,
};

for (var i = 0; i < 8; i++) {
    option_raw.series.push({
        name: 'CH' + (i + 1),
        type: 'line',
        showSymbol: false,
        hoverAnimation: false,
        smooth: false,
        data: [],
        animationDurationUpdate: 10,
        itemStyle: {
            normal: {
                lineStyle: {
//                    color: colors[i],
                    width: 0.6,
                }
            }
        }
    });
}

var option_pwr = {
    grid: {
        top: 40,
        left: 45,
        bottom: 35,
        right: 35,
    },
    toolbox: {
        feature: {
            myPauseAndResume: {
                show: true,
                title: '开始',
                icon: 'path://M424.4 214.7L72.4 6.6C43.8-10.3 0 6.1 0 47.9V464c0 37.5 40.7 60.1 72.4 41.3l352-208c31.4-18.5 31.5-64.1 0-82.6z',
                onclick: function() {
                    echartPause(option_pwr);
                    chart_pwr.setOption(option_pwr);
                },
            },
            dataZoom: {},
            dataView: {},
            restore: {},
            saveAsImage: {
                name: 'DBS-Freq-Display',
                title: '保存图片',
            },
            magicType: {
                type: ['line', 'bar', 'tiled']
            }
        },
//        top: 32,
//        right: 8,
//        orient: 'vertical'
    },
    xAxis: {
        type: 'value',
        name: 'Frequency / Hz',
        nameLocation: 'middle',
        min: 'dataMin',
        max: 'dataMax',
        axisPointer: {
            show: true,
            type: 'line',
        },
    },
    yAxis: {
        type: 'value',
        name: 'Amplitude / V',
        nameLocation: 'end',
        nameTextStyle: {
            padding: [0, 0, -5, 0]
        },
        axisPointer: {
            show: true,
            type: 'line',
        },
    },
    series: {
        name: 'test',
        type: 'line',
        showSymbol: false,
        hoverAnimation: true,
        smooth: true,
        data: [],
        itemStyle: {
            normal: {
                lineStyle: {
                    color: nowColor,
                    width: 1
                }
            }
        }
    },
};