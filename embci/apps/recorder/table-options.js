var columns = [
    {rowHandle: true, formatter: 'handle', headerSort: false},
    {
        formatter: 'rowSelection', titleFormatter: 'rowSelection',
        align: 'center', headerSort: false, visible: false,
    },
    {title: 'ID', field: 'id', sorter: 'number', width: 40},
    {title: 'Name', field: 'info.name', sorter: 'alphanum'},
    {
        title: 'Record', field: 'gen.recording', align: 'center', width: 40,
        headerSort: false, headerVertical: true,
        formatter: 'traffic', formatterParams: {min: 0, max: 2},
        mutator: (value, data, type, params, component) => {
            switch (data.info.status) {
                case 'started':
                case 'resumed':
                    return 2;
                case 'paused':
                    return 1;
                case 'closed':
                default:
                    return 0;
            }
        },
        cellClick: (e, cell) => recorderCommand(
            cell.getData().info.name,
            (
                cell.getData().info.username &&
                cell.getData().gen.recording == 1
            ) ? 'resume' : 'pause',
            () => table.setData()
        ),
    },
    {
        title: 'Status', field: 'info.status', headerSort: false,
        formatter: cell => cell.getValue().toUpperCase(),
    },
    {title: 'CTRL', columns: [], visible: false},
    {
        title: 'Control', field: 'gen.control', align: 'center', width: 40,
        headerSort: false, headerVertical: true,
        formatter: (cell) => {
            if (!cell.getData().gen.recording) {
                return '<span class="fas fa-play" style="color:green"></span>';
            } else {
                return '<span class="fas fa-stop" style="color:red"></span>';
            }
        },
        cellClick: (e, cell) => recorderCommand(
            cell.getData().info.name,
            cell.getData().gen.recording ? 'close' : 'start',
            () => table.setData()
        ),
    },
    {
        title: 'Username', field: 'info.username',
        sorter: 'alphanum', sorterParams: {alignEmptyValues: 'bottom'},
        editor: 'input', editorParams: {search: true},
        cellEdited: (cell) => recorderCommand(
            cell.getData().info.name, {username: cell.getValue()}
        ),
    },
    {title: 'Buffer', columns: [
        {
            title: 'Space', field: 'gen.buffer_ratio', sorter: 'number',
            mutator: (v, d) => d.info.buffer_nbytes / d.info.buffer_max,
            formatter: 'progress', formatterParams: {
                max: 1, legend: v => 100 * v + '%', legendColor: 'blue'
            },
            cellClick: (e, cell) => recorderCommand(cell.getData().info.name),
        },
        {title: 'Num', field: 'info.buffer_length', sorter: 'number'},
        {
            title: 'Size', field: 'info.buffer_nbytes', sorter: 'number',
            formatter: (cell) => {
                let val = cell.getValue();
                if (val < 2**10) return val + ' Bytes';
                else if (val < 2**20) return (val / 2**10).toFixed(2) + ' KB';
                else if (val < 2**30) return (val / 2**20).toFixed(2) + ' MB';
                else return (val / 2**30).toFixed(3) + ' GB';
            },
        },
    ]},
    {
        title: 'Chunk', field: 'info.chunk', headerSort: false,
        editor: 'number', editorParams: {max: 10}, cellEdited: (cell) => {
            recorderCommand(cell.getData().info.name, {chunk: cell.getValue()});
        },
    },
    {title: 'EventIO', columns: [
        {
            title: 'Merge', field: 'info.event_merge', headerSort: false,
            align: 'center', width: 50, formatter: 'tickCross',
            cellClick: (e, cell) => recorderCommand(
                cell.getData().info.name, {event_merge: !cell.getValue()}
            ),
        },
        {
            title: 'Code', field: 'gen.event_code', headerSort: false,
            align: 'center', width: 50,
            mutator: (value, data) => data.info.event[0] || 'None',
            editor: 'select', editable: () => window.eventList != undefined,
            editorParams: (cell) => ({
                values: (window.eventList || []).reduce((map, event) => {
                    if (!event.name in map) {
                        map[event.name] = event.code;
                    }
                    return map;
                }, {}),
            }),
            cellEdited: (cell) => recorderCommand(
                cell.getData().info.name, {event: cell.getValue()}
            ),
        },
        {
            title: 'Time', field: 'gen.event_time', sorter: 'number',
            sorterParams: {alignEmptyValues: 'bottom'}, align: 'center',
            mutator: (value, data) => data.info.event[1] * 1000 || undefined,
            formatter: (cell, params, cb) => {
                if (!cell.getValue()) return 'None';
                let time = new Date(cell.getValue());
                return time.toISOString().replace('T', ' ').replace('Z', '');
            },
        },
    ]},
    {
        title: 'ThreadID', field: 'info.ident', sorter: 'number', visible: true,
        formatter: cell => '0x' + parseInt(cell.getValue()).toString(16),
    },
    {
        title: 'Stream', field: 'info.source', sorter: 'alphanum', visible: true,
        editor: 'select', editorParams: (cell) => ({
            values: true || 'source_list',
        }),
        // cellEdited: (cell) => recorderCommand(cell),
    },
];
