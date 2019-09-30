// ============================================================================
// Keyboard GUI & Flickers Rendering

function renderAlphabets(ctx, lout, detail=false, border=false) {
    lout = lout || layout;
    var size = lout && lout[0].h || 32;
    if (detail) {
        ctx.font = 'bold ' + (size / 4).toFixed(0) + 'px monospace';
    } else {
        ctx.font = 'bold ' + (size / 2).toFixed(0) + 'px monospace';
    }
    ctx.textAlign = 'center';
    ctx.clear();
    for (var blick, i = 0; i < lout.length; i++) {
        block = lout[i];
        offset = ctx.measureText(block.name).width / 2;
        if (detail) {
            ctx.lineWidth = 1;
            ctx.fillStyle = 'blue';
            ctx.fillText(
                (block.freq / 2 / Math.PI).toFixed(1),
                block.x + block.w / 4 * 1.5,
                block.y + block.h / 4 * 1 + offset
            );
            ctx.fillStyle = 'red';
            ctx.fillText(
                (block.phase / Math.PI).toFixed(2),
                block.x + block.w / 4 * 2.5,
                block.y + block.h / 4 * 3 + offset
            );
            ctx.fillStyle = 'black';
            ctx.beginPath();
            ctx.moveTo(block.x + block.w, block.y + block.h / 3);
            ctx.lineTo(block.x, block.y + block.h - block.h / 3);
            ctx.closePath();
            ctx.stroke();
        } else {
            ctx.fillStyle = 'black';
            ctx.fillText(
                block.name,
                block.x + block.w / 2,
                block.y + block.h / 2 + offset
            );
        }
        if (border && (border == block.name)) {
            ctx.strokeStyle = '#d11';
            ctx.lineWidth = 6;
            ctx.strokeRect(block.x + 3, block.y + 3, block.w - 6, block.h - 6);
        }
    }
}

function renderBlockExtend(ctx, block, method=1) {
    switch (method) {
        case 1: // draw rectangle on 2D canvas
            ctx.fillStyle = colors[0 + block.on];
            ctx.fillRect(block.x, block.y, block.w, block.h);
            break;
        case 2: // draw rectangle on WebGL canvas
            ctx;
            break;
        case 3: // update css of target element
            $('#block-' + block.name).toggleClass('invert');
            /*
            if (block.on) {
                $('#block-' + block.name).removeClass('invert');
            } else {
                $('#block-' + block.name).addClass('invert');
            }
            */
            break;
    }
}

function renderBlock(ctx, block) {
    ctx.fillStyle = colors[0 + block.on];
    ctx.fillRect(block.x, block.y, block.w, block.h);
}

function renderBlocks(ctx, lout=layout) {
    ctx.clear();
    for (var i = 0; i < lout.length; i++) {
        lout[i].on = true;
        renderBlock(ctx, lout[i]);
    }
}
        
function stateBlocks(ts) {
    /* DO NOT clear onscreen canvas!! */
    /* Timestamp must be float and in MICROSECONDS!! */
    // ts = ts || performance.now() || Date.now();
    for (var st, block, i = 0; i < layout.length; i++) {
        block = layout[i];
        st = Math.sin(block.freq * ts / 1000 + block.phase) > 0;
        if (block.on == st) continue;
        block.on = st;
        renderBlock(ctx, block);
    }
}

function stateBlocksOffScreen(ts) {
    /* DO NOT clear onscreen canvas!! */
    /* Timestamp must be float and in MICROSECONDS!! */
    // ts = ts || performance.now() || Date.now();
    // ctxOs.clear(); /* renderBlock won't change layout, so this is optional */
    for (var st, block, i = 0; i < layout.length; i++) {
        block = layout[i];
        st = Math.sin(block.freq * ts / 1000 + block.phase) > 0;
        if (block.on == st) continue;
        block.on = st;
        /* draw on offscreen virtual canvas */
        renderBlock(ctxOs, block);
    }
    /* update to onscreen displayed canvas */
    ctx.drawImage(ctxOs.canvas, 0, 0);
}

function blinkBlocks(interval, verbose=false, callback=null) {
    /* 1. Send session.start event.
     * 2. Blink flickers for `interval` in ms, `verbose` to log more info.
     * 3. Send session.stop event.
     * 4. Re-render keyboard area.
     * */
    eventSend('session.start');
    return LoopTask(stateBlocks, interval, verbose)
        .byTimeout()
        .done(function() {
            eventSend('session.stop');
            renderBlocks(ctx, layout);
            renderAlphabets(ctxAl, layout);
            callback && callback();
        });
}

// ===========================================================================
// SSVEP Experiment Session

function sessionStart() {
    eventSend('session.init');
}

function sessionStartOld(interval, id=null) {
    function error(xhr, status, error) {
        alert('Cannot start session: ' + error);
        sessionStop(false);
        $('#session-ctrl').trigger('trialStop');
    }
    $.ajax({
        url: 'sess/start',
        method: 'GET',
        data: {timeout: interval, id: id},
        dataType: 'json',
        success: function(msg) {
            if (!msg['recorder.start']) return error();
            sessID = msg['recorder.start'];
            blinkBlocks(interval, verbose=true).done(() => {
                sessionStop(true);
                $('#session-ctrl').trigger('trialStop');
            });
        },
        error: error
    });
}

function sessionStop(result=false) {
    eventSend('session.end', {result: result});
}

function sessionStopOld(result=false) {
    $.ajax({
        url: 'sess/stop',
        method: 'GET',
        data: {id: sessID, result: result},
        dataType: 'json',
        success: function(msg) {
            if (!result) {
                if (msg['recorder.stop'] != sessID) {
                    console.error('Session ID mis-match when session.stop');
                    sessionResult(sessID);
                } else sessID = null;
                return;
            }
            if (!msg['result']) {
                console.error('Session result not returned.'); return;
            }
            selectAlphabet(layout[msg['result'].index].name);
        },
        error: function(xhr, status, error) {
            if (result) alert('Cannot stop session: ' + error);
            else console.error('Cannot stop session, no result will be fetched');
        }
    });
}

function sessionResult(id=null, maxtry=3) {
    $.ajax({
        url: 'sess/result',
        method: 'GET',
        data: {id: id || sessID},
        dataType: 'json',
        success: function(rst) {
            var idx = rst['index'];
            var arr = rst['array'];
            selectAlphabet(layout[idx].name);
        },
        error: function(xhr, status, error) {
            console.error('Session result failed to load: ' + error);
            --maxtry && setTimeout(() => sessionResult(id, maxtry), 150);
        }
    });
}

function sessionToggle(target) {
    if (!target) return;
    $.get({url: 'sess/' + target, error: rst  =>  console.warn(rst)});
}

// ============================================================================
// Some useful functions used in EmBCI SSVEP WebUI

function eventSend(code_or_name, extra=null) {
    for (var event=null, i = 0; i < eventList.length; i++) {
        if (eventList[i].name != code_or_name &&
            eventList[i].code != code_or_name) continue;
        event = eventList[i];
    }
    if (!event) {
        console.error('Unknown event to send', code_or_name);
        return;
    } else if (extra) {
        event = _.extend(event, extra);
    }
    console.log('Sending event', event, Date.now() / 1000);
    if (wsEvent) {
        wsEvent.send(JSON.stringify(event));
    } else {
        $.ajax({
            url: 'event',
            method: 'GET',
            data: {'event': JSON.stringify(event)},
            success: (msg) => {msg && console.log(msg)},
            error: (xhr, status, error) => (console.error(error))
        });
    }
}

function selectAlphabet(char) {
    var e = document.getElementById('input-result');
    if (char in callbacks) {
        callbacks[char](e);
    } else {
        if (char == '<') {
            e.value = e.value.slice(0, -1);
        } else e.value += char;
    }
}

function setContext(canvas, ctxType, cfg) {
    var ctx;
    if (!canvas.getContext) {
        alert('Invalid canvas HTML element.');
        return;
    }
    switch (ctxType) {
        case '2d':
            ctx = canvas.getContext('2d', cfg);
            break;
        case 'webgl':
            ctx = canvas.getContext('webgl', cfg) ||
                canvas.getContext('experimental-webgl', cfg);
            break;
        case 'webgl2':
            ctx = canvas.getContext('webgl2', cfg);
            break;
        case 'bitmaprender':
            ctx = canvas.getContext('bitmaprender', cfg);
            break;
        default:
            alert('Invalid context type: ' + ctxType);
            return;
    }
    if (ctx != null) {
        if (!ctx.clear) {
            ctx.clear = function() {
                this.clearRect(0, 0, this.canvas.width, this.canvas.height);
            }
        }
        return ctx;
    }
    alert('Your browser or machine do not support context: ' + ctxType);
    return;
}

function loadLayoutNames() {
    return $.getJSON('kbd/layout', function(lst) {
        layoutNames = lst;
        $s = $('#select-layouts');
        $s.children('option:not([hidden])').remove();
        layoutNames.forEach((name) => $s.append(`<option>${name}</option>`));
    });
}

/*
layout = {
    "name": "/path/to/layout-filename.json",
    "blocks": [{
        "name": "alphabet",
        "freq": 2 * Math.PI * freq(in Hz)c`, "phase": in rad,
        "x": coordinate, "y": in pixel,
        "w": width, "h": height,
        "on": true,
    }, ...]
}['blocks']
 */
function loadLayoutByName(name) {
    if (!layoutNames.length) {
        console.error('No available layout.');
        return;
    } else if (!layoutNames.includes(name)) {
        console.error('Invalid layout name: ' + name);
        name = layoutNames[0];
    }
    console.log('Loading layout: ' + name);
    return $.getJSON('kbd/layout/' + name, function(obj) {
        console.log('Using layout file: ' + obj.name);
        for (var block, i = 0; i < obj.blocks.length; i++) {
            block = obj.blocks[i];
            block.freq *= 2 * Math.PI;
            block.x -= block.w / 2;
            block.y -= block.h / 2;
            block.on = true;
        }
        layout = obj.blocks;
    });
}

function loadEventList() {
    return $.getJSON('event/list', function(lst) {
        eventList = [];
        for (event of lst) {
            if (!event.name || !event.code) continue;
            eventList.push(event);
        }
    });
}

// ============================================================================
// Debug

function test_status(ts) {
    ts = ts || performance.now();
    for (var state, block, i = 0; i < layout.length; i++) {
        block = layout[i];
        state = Math.round(Math.sin(block.freq * ts + block.phase));
        block.on = state > 0;
        console.log(state, block.on);
    }
}

function test_loop_flickers(timeout=2000, times=100, delay=1000) {
    console.log('Iteration', times);
    blinkBlocks(timeout, verbose=true, sessionStop);
    if (--time) {
        setTimeout(() => test_loop_flickers(timeout, time), timeout + delay);
    }
}

function test_random_flickers(timeout=2000, times=100, delay=3000) {
    var block = layout[Math.floor(Math.random() * layout.length)];
    console.log('Iteration', times, 'will blink block `' + block.name + '`');
    renderAlphabets(ctxAl, layout, false, block.name);
    setTimeout(() => {
        eventSend('session.alphabet', {char: block.name});
        blinkBlocks(timeout, verbose=true, sessionStop);
    }, delay - 10);
    if (--times) {
        window.id_test = setTimeout(() => {
            test_random_flickers(timeout, times, delay);
        }, timeout + delay + 10);
    }
}

function blink_random_flickers(timeout=2000, times=100, delay=2000) {
    // var block = layout[times%layout.length];
    var block = layout[Math.floor(Math.random() * layout.length)];
    console.log('Iteration', times, 'will blink block `' + block.name + '`');
    renderAlphabets(ctxAl, layout, false, block.name);
    /* you can stop here */
    window.id_train = setTimeout(() => {
        eventSend('session.alphabet', {char: block.name});
        blinkBlocks(timeout, verbose=true, sessionStop);
        /* also you can stop here */
        window.id_train = setTimeout(() => {
            if (--times) blink_random_flickers(timeout, times, delay);
            else $('#session-auto').click();
        }, timeout + 100);
    }, delay - 100);
}
