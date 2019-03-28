var colors = ['#0000FF', '#80FF10', '#FF11FF', '#00FFFF', '#00FF00', '#FF0000', '#800080', '#FFA00A', '#202020'];
var nowColor = colors[0];

var option1 = {
    grid: {
        top: 25,
        bottom: 50
    },
    animationDurationUpdate: 1,
    xAxis: {
        type: 'value',
        name: 'Time/s',
        nameLocation: 'middle',
        nameTextStyle: {
            padding: [15, 0, 0, 0]
        },
        max: 1,
        min: 0,
        splitLine: {
            show: false
        },
        axisLine: {
            lineStyle: {
                color: '#333'
            },
            onZero: false
        }
    },
    yAxis: {
        type: 'value',
        name: 'Voltage/V',
        nameLocation: 'end',
        nameTextStyle: {
            padding: [0, 0, -10, 0]
        },
        axisLine: {
            lineStyle: {
                color: '#333'
            }
        },
        splitLine: {
            show: false
        },
        boundaryGap: ['10%', '10%'],
        max: 0.5,
        min: -0.5
    },
    series: {
        name: 'test',
        type: 'line',
        showSymbol: false,
        hoverAnimation: false,
        smooth: false,
        data: [],
        animationDurationUpdate: 10,
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


var option2 = {
    grid: {
        top: 15,
        bottom: 40
    },
    xAxis: {
        type: 'value',
        name: 'Frequency/Hz',
        nameLocation: 'middle',
        min: 0,
        max: 25,
        nameTextStyle: {
            padding: [15, 0, 0, 0]
        },
        axisLine: {
            lineStyle: {
                color: '#333'
            }
        }
    },
    yAxis: {
        type: 'value',
        name: 'Amp/V',
        nameLocation: 'end',
        nameTextStyle: {
            padding: [0, 0, -10, 0]
        },
        boundaryGap: ['0%', '20%'],
        axisLine: {
            lineStyle: {
                color: '#333'
            }
        }
    },
    series: {
        name: 'test',
        type: 'line',
        showSymbol: false,
        hoverAnimation: true,
        smooth: false,
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