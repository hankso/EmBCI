What is a Speller System
------------------------
A speller system is a special system design for disabilities to ``spell`` words with brain, which is also known as **Mind Typing**. In EmBCI, the Speller app integrates a web user interface and some bio-signal analysis algorithms. It displays array of blocks on webpage. Each block is marked with an alphabet and will blink in a specific frequency. EEG signal of users will also be recorded simultaneously. By analyzing EEG data, we can find out which block user is gazing at, thus the alphabet of that block is **typed**.

Users can watch the UI through computer, tablet or even mobile phone. 


Technique details
-----------------
Display stimulus using HTML + JS + CSS
======================================
The most important work of rendering stimulus on webpage is to ensure that the frequency of flickers are constant and equal to the setting value. Color changing of stimulus must be strictly evenly spaced.

setTimeout and setInterval
==========================
Using function **setTimeout(handler[, timeout])** and **setInterval(handler[, timeout])** to render animation of flickers has two disadvantages:

First, it's not easy to select a proper timeout. The most frequently used value is 17ms (1000ms / 60FPS), but the real display refresh rate depends on the screen and driver.

Secondly, setTimeout and setInterval only stack functions to be executed in a queue of browser UI process, not actually call them. If UI process is busy, functions will not be called in time.

As a better choice in this project, **window.requestAnimationFrame** is used to render flickers.

requestAnimationFrame
=====================
The rAF is a relatively new API, recommended to be used for implementing interactive applications in the browser. This method ask the browser to call the callback function before the next repaint. As W3C recommended, rAF execution frequency match the real display refresh rate in most web browsers.

HTML Canvas
===========
HTML <canvas> element is one of the most widdly used tools for rendering 2D graphics on the web. However, when websites and apps push the Canvas API to its limits (for example 60FPS), performance begins to suffer. Canvas supports many different backends including `2D`, `webgl`, `bitmaprender` etc. In this project `2D` backend with multi-offscreen canvas and `WebGL` backend are employed to make the best use of canvas for better render performance.

Canvas 2D backend
=================
In morden browsers, whenever something happens that changes a webpage's look or content, the browser will schedule a repaint operation soon after the changing to update page. Because repaints can be an expensive operation to CPU, it's better and much faster to draw animation on an offscreen canvas and render the whole scene once to the onscreen canvas.

For example, when you need to inverse the color of block `a`, `c` and `z`::
    for (var blk, i = 0; i < 3; i++) {
        blk = [blockA, blockC, blockZ][i];
        if (blk.on) ctx.fillStyle = 'black';
        else        ctx.fillStyle = 'white';
        blk.on = !blk.on;                         // inverse color
        ctx.fillRect(blk.x, blk.y, blk.w, blk.h); // draw on main canvas
    }

It needs three repaints (3 * 1000/60 = 50ms) to render this color changes, one for each block. In other words, if only one canvas is used, color changes is done in memory, but not updated to screen yet. So offscreen canvas is widely used for `draw multiple items & render once time`. Offscreen canvas is actually a canvas element that is not included in HTML element tree::
    // Create the offscreen canvas after whole HTML document is loaded.
    var ctxOs = document.createElement('canvas').getContext('2d');
    // Offscreen canvas will be rendered on main canvas later, so must match size
    ctxOs.canvas.width = mainCanvas.width;
    ctxOs.canvas.height = mainCanvas.height;

Although we use requestAnimationFrame instead of setTimeout (multiple drawings will be handled inside one repaint), using offscreen canvas is still preferred. So, to inverse color of blocks the code will be::
    for (var blk, i = 0; i < blocks.length; i++) {
        blk = blocks[i];
        if (blk.on) ctxOs.fillStyle = 'black';
        else        ctxOs.fillStyle = 'white';
        blk.on = !blk.on;                           // inverse color
        ctxOs.fillRect(blk.x, blk.y, blk.w, blk.h); // draw on offscreen canvas
    }
    ctx.drawImage(ctxOs.canvas, 0, 0);              // render to onscreen canvas

Alpha channel(transparency) of keyboard canvas is disabled to optimize the performance. And alphabets are rendered on an individual canvas above keyboard layer because this layer doesn't need to be redrawn once initialized.


Optimization
------------
Using code below to calculate the real frames per second::
    timeout = 300;  // 300ms
    function loopTask(ts) {
        if (!starttime) starttime = ts;
        if ((ts - starttime) < timeout) {
            requestAnimationFrame(loopTask);
        } else taskDone = true;
        time1 = performance.now();
        blinkBlocks(layout)
        time2 = performance.now();
        fps = 1000 / (time2 - time1);
        console.log(
            'Frame start at', ts.toFixed(2),
            'latency', (time2 - ts).toFixed(2),
            'end at', time2.toFixed(2),
            'used time', time2 - time1,
            'FPS', fps.toFixed(2)
        );
    }

Start session by ``loopTask(performance.now())``. And the log information will be something like::
