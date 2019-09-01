
$(function () {
    var e = $('nav#headbar #batteryBar');
    e.children('button.btn').hide();
    if (!e[0]) return;
    var batteryBar = new ProgressBar.Circle(e[0], {
        color: '#7733FF',
        duration: 500,
        easing: 'easeInOut',
        strokeWidth: 4,
        trailColor: '#E3E3E3',
        trailWidth: 0.8,
        text: {
            value: '',
            style: {
                color: '#888888',
                position: 'absolute',
                top: '50%',
                left: '50%',
                padding: 0,
                margin: 0,
                transform: {
                    prefix: true,
                    value: 'translate(-50%,-50%)'
                }
            }
        }
    });

    function updateBatteryLevel() {
        $.ajax({
            url: '/apps/system/battery',
            method: 'GET',
            success: function (msg) {
                batteryBar.animate(parseInt(msg) / 100.0);
                batteryBar.setText(msg + '%');
            },
            error: function () {
                batteryBar.animate(0);
                batteryBar.setText('E');
            }
        });
    }
    
    var b_interval;
    e.on('click', function () {
        // toggle battery interval state
        b_interval = b_interval ? (
            batteryBar.animate(0) ||
            batteryBar.setText('') ||
            clearInterval(b_interval)
        ) : (
            updateBatteryLevel() ||
            setInterval(updateBatteryLevel, 10000)
        );
    });
    e.click();
});
