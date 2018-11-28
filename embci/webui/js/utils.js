
function timeit(func, iters) {
            var results = [];
            var total = 0;
    for (var i = 0; i < iters; i++) {
        var start = performance.now();
        func();
        var end = performance.now();
        var duration = end - start;
        results.push(duration);
        total += duration;
    }
    var result = {
        results: results,
        total: total,
        avg: total / results.length 
    }
    return result;    
}

function TimeIt() {
    var self = this;
    self.timeit = timeit;
}
