/* for compatiability */
window.requestAnimationFrame = (
    window.requestAnimationFrame       ||           // Chromium  
    window.webkitRequestAnimationFrame ||           // Webkit 
    window.mozRequestAnimationFrame    ||           // Mozilla Geko 
    window.oRequestAnimationFrame      ||           // Opera Presto 
    window.msRequestAnimationFrame                  // IE Trident? 
) || (callback => window.setTimeout(callback, 17)); // Fallback function 

window.cancelAnimationFrame = (
    window.cancelAnimationFrame    ||
    window.mozCancelAnimationFrame
) || window.clearTimeout;

var LoopTask = function(callback, timeout=1000, verbose=false) {
    var fps = 0;
    var frame = 0;         // loop counter
    var run = false;       // lock used to avoid multi-start
    var done = false;      // indicate loop task finished
    var doneHooks = [];    // function to be executed after task finished
    var donetime = 0;      // when loop task finished
    var lasttime = 0;      // calculate real FPS
    var thistime = 0;      // calculate real FPS
    var starttime = 0;     // stopByTimeout: check whether timeout
    var req_id = null;     // stopByCancel:  save rAF ID for cancellation

    function loop(ts) {
        if (!lasttime) lasttime = ts;
        callback(ts);
        thistime = performance.now();
        fps = 1000 / (thistime - lasttime);
        if (fps < 40) {
            console.warn(
                'Frame', frame++, 'lost warning!', 
                'start at', ts.toFixed(2),
                'end at', thistime.toFixed(2),
                'exec time', (thistime - ts).toFixed(2),
                'frame time', (thistime - lasttime).toFixed(2),
                'FPS', fps.toFixed(2)
            );
        }
        if (verbose > 1) {
            console.log(
                'Frame', frame++,
                'start at', ts.toFixed(2),
                'end at', thistime.toFixed(2),
                'exec time', (thistime - ts).toFixed(2),
                'frame time', (thistime - lasttime).toFixed(2),
                'FPS', fps.toFixed(2)
            );
        }
        lasttime = thistime;
    }

    function stopByTimeout(ts) {
        /* schedule next execution */
        if (!starttime) starttime = ts;
        if ((ts - starttime) < timeout) {
            window.requestAnimationFrame(stopByTimeout);
            loop(ts);
        } else {
            done = true; donetime = Date.now() / 1000;
            verbose && console.log('LoopTask finished at', donetime);
            for (cb of doneHooks) window.requestAnimationFrame(cb);
        }
    }
    
    function stopByCancel(ts) {
        /* schedule next execution */
        req_id = window.requestAnimationFrame(stopByCancel);
        loop(ts);
    }

    return {
        byTimeout: function() {
            if (run) return this; else run = true;
            verbose && console.log('LoopTask start at', Date.now() / 1000);
            window.requestAnimationFrame(stopByTimeout);
            return this;
        },
        byCancel: function() {
            if (run) return this; else run = true;
            verbose && console.log('LoopTask start at', Date.now() / 1000);
            window.requestAnimationFrame(stopByCancel);
            setTimeout(function() {
                window.cancelAnimationFrame(req_id);
                done = true; donetime = Date.now() / 1000;
                verbose && console.log('LoopTask finished at', donetime);
                for (cb of doneHooks) window.requestAnimationFrame(cb);
            }, timeout);
            return this;
        },
        displayFPS: function(id, update=100) {
            if (!run) return this;
            var $e = $('#' + id);
            if ($e.length != 1) return this;
            var oldcolor = $e.css('color');
            $e.css('color', 'green');
            (function render() {
                if (!done) {
                    setTimeout(render, update);
                } else {
                    $e.css('color', oldcolor);
                    return;
                }
                if (fps && fps != Infinity) {
                    $e.text('FPS: ' + fps.toFixed(2));
                }
            })();
            return this;
        },
        done: function(callback) { doneHooks.push(callback); return this; }
    }
}
