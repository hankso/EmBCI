var option_raw = {
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
        right: 8,
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
        max: 9, 
//        max: (v) => Math.min(Math.ceil(v.max), 9),
        min: 0,
//        min: (v) => Math.floor(v.min),
        interval: 1
    }],
    series: [],
    animationDurationUpdate: 1,
};

var option_pwr = {
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
            myLoopTask: {
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
                type: ['line', 'bar']
            }
        },
        right: 8
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
        name: 'Amplitude / mV',
        nameLocation: 'end',
        nameTextStyle: {
            padding: [0, 0, -5, 0]
        },
        axisPointer: {
            show: true,
            type: 'line',
        },
    },
    series: []
};

for (var i = 0; i < 8; i++) {
    option_raw.series.push({
        name: i,
        type: 'line',
        showSymbol: false,
        hoverAnimation: false,
        smooth: false,
        data: [],
        animationDurationUpdate: 5,
        itemStyle: {
            normal: {
                lineStyle: {
                    width: 0.8,
                }
            }
        }
    });
    option_pwr.series.push({
        name: i,
        type: 'line',
        showSymbol: false,
        smooth: true,
        data: [],
        itemStyle: {
            normal: {
                lineStyle: {
                    width: 0.4
                }
            }
        }
    });
}