var columns = [
    {rowHandle: true, formatter: 'handle', headerSort: false, visible: false},
    {
        formatter: 'rowSelection', titleFormatter: 'rowSelection',
        align: 'center', headerSort: false, visible: false,
    },
    {
        title: 'Filename', field: 'filename', sorter: 'alphanum',
        formatter: 'link', formatterParams: {urlField: 'link', target: '_blank'},
    },
    {
        title: 'Label', field: 'gen.label', sorter: 'alphanum', responsive: 3,
        mutator: (value, data) => data.filename.split('-')[0],
    },
    {
        title: 'Format', field: 'gen.format', sorter: 'string', responsive: 4,
        mutator: (value, data) => {
            let snip = data.filename.split('.');
            return snip[snip.length - 1];
        }
    },
    // {title: 'Information', columns: [
        {
            title: 'Mode', field: 'stat.st_mode', headerSort: false,
            responsive: 3, formatter: (cell) => {
                // return string like [d|s|l|-]rwxrwxrwx
                let mode = cell.getValue().toString(8), rst = '';
                for (let bit, i = 3; i > 0; i--) {
                    bit = mode[mode.length - i];
                    rst += bit & 0b100 ? 'r' : '-';
                    rst += bit & 0b010 ? 'w' : '-';
                    rst += bit & 0b001 ? 'x' : '-';
                }
                return rst;
            }
        },
        {
            title: 'Size', field: 'stat.st_size', sorter: 'number',
            formatter: (cell) => {
                let val = cell.getValue();
                if (val < 2**10) return val + ' Bytes';
                else if (val < 2**20) return (val / 2**10).toFixed(2) + ' KB';
                else if (val < 2**30) return (val / 2**20).toFixed(2) + ' MB';
                else return (val / 2**30).toFixed(3) + ' GB';
            },
        },
        {
            title: 'Last Modified', field: 'stat.st_mtime', sorter: 'number',
            responsive: 2, formatter: (cell, params, cb) => {
                if (!cell.getValue()) return 'None';
                let time = new Date(cell.getValue() * 1000);
                return time.toISOString().replace('T', ' ').replace('Z', '');
            },
        },
    // ]},
    {
        field: 'gen.delete', align: 'center', width: 40, headerSort: false,
        formatter: (cell) => {
            return '<span class="fas fa-trash-alt" style="color:red"></span>';
        },
        cellClick: (e, cell) => {
            let prompt = `Delete data file ${cell.getData().filename}?`;
            let link = cell.getData().link;
            if (!window.confirm(prompt)) return;
            $.ajax(link, {method: 'DELETE', success: () => table.setData()});
        },
    },
    {
        field: 'gen.download', align: 'center', width: 40, headerSort: false,
        formatter: (cell) => {
            return $('<a class="fas fa-download">')
                .attr('href', cell.getData().link + '?download=true')
                .attr('target', '_blank')[0];
        },
    },
];
