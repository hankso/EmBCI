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

setTimeout(() => window.requestAnimationFrame(function getFPS(ts, times=5) {
    if (window.FPS != undefined) window.FPS.push(ts); else window.FPS = [ts];
    if (--times) window.requestAnimationFrame(ts => getFPS(ts, times));
    else {
        for (var sum = 0, i = 1, l = window.FPS.length; i < l; i++) {
            sum += window.FPS[i] - window.FPS[i - 1];
        }
        window.FPS = 1000 / (sum / (l - 1));
        console.log('Browser refresh rate detected as', window.FPS.toFixed(2), 'Hz');
    }
}), 3000);

var LoopTask = function(callback, timeout=1000, verbose=false) {
    var fps = 0;
    var frame = 0;         // loop counter
    var run = false;       // lock used to avoid multi-start
    var done = false;      // indicate loop task finished
    var doneHooks = [];    // function to be executed after task finished
    var donetime = 0;      // when loop task finished
    var lasttime = 0;      // calculate real FPS
    var thistime = 0;      // calculate real FPS
    var starttime = 0;     // used to sync all duration
    var duration = 0;      // time passed since task start
    var req_id = null;     // used by stopByCancel / forceStop
    var tout_id = null;    // used by displayFPS / forceStop

    function loop(ts) {
        if (!lasttime) lasttime = performance.now();
        callback(ts);
        thistime = performance.now();
        fps = 1000 / (thistime - lasttime);
        if (fps < FPS / 2) {
            console.warn(
                'Frame', frame++, 'lost warning!', 
                'start at', (starttime + ts).toFixed(2),
                'end at', thistime.toFixed(2),
                'frame time', (thistime - lasttime).toFixed(2),
                'FPS', fps.toFixed(2)
            );
        }
        if (verbose > 1) {
            console.log(
                'Frame', frame++, 'dt', ts.toFixed(2),
                'start at', (starttime + ts).toFixed(2),
                'end at', thistime.toFixed(2),
                'frame time', (thistime - lasttime).toFixed(2),
                'FPS', fps.toFixed(2)
            );
        }
        lasttime = thistime;
    }

    function byTimeout(ts) {
        duration = ts - starttime;
        if (duration >= timeout) return taskStop();
        req_id = window.requestAnimationFrame(byTimeout);
        loop(duration);
    }
    function byCancel(ts) {
        req_id = window.requestAnimationFrame(byCancel);
        loop(ts - starttime);
    }
    function taskStart(ts) {
        verbose && console.log('LoopTask start at', Date.now() / 1000);
        starttime = ts || Date.now();
    }
    function taskStop() {
        done = true; donetime = Date.now() / 1000;
        verbose && console.log('LoopTask finished at', donetime);
        for (cb of doneHooks) window.requestAnimationFrame(cb);
    }
    function forceStop() {
        window.cancelAnimationFrame(req_id);
    }

    return {
        byTimeout: function() {
            if (!run) run = true; else return this;
            window.requestAnimationFrame((ts)=>{
                taskStart(ts); byTimeout(ts);
            });
            return this;
        },
        byCancel: function() {
            if (!run) run = true; else return this;
            window.requestAnimationFrame((ts)=>{
                taskStart(ts); byCancel(ts);
            });
            tout_id = setTimeout(forceStop, timeout);
            taskStop();
            return this;
        },
        forceStop: function() {
            forceStop();
            window.clearTimeout(tout_id);
            taskStop();
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
