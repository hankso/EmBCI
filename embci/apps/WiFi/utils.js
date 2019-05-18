var ap_list = [];

function get_ap_by_ssid(ssid) {
    for (var i = 0; i < ap_list.length; i++) {
        if (ap_list[i].ssid == ssid) {
            return ap_list[i];
        }
    }
}

function wifi_enabled() {
    return $('#wifi-switch-checkbox')[0].checked;
}

function refresh() {
    if (!wifi_enabled()) {
        return update_wifi_status();
    }
    var ph = $('#nowifi-placeholder');
    var wc = $('#wifi-container');
    $.ajax({
        method: 'GET',
        url: 'hotspots',
        dataType: 'json',
        success: function (data) {
            ap_list = data.list;
            wc.empty();
            if (ap_list.length == 0) {
                ph.show();
            } else {
                ph.hide();
                for (var i = 0; i < ap_list.length; i++) {
                    wc.append(render(ap_list[i]));
                }
            }
        },
        error: function () {
            ph.show();
            wc.empty();
        }
    });
}

function parse_enc(ap) {
    var list = ap.encryption_type;
    var rst = [];
    for (var i = 0; i < list.length; i++) {
        rst.push(list[i]);
    }
    return ['WPA'];
}

function parse_fre(ap) {
    var list = ap.frequency;
    var rst = [];
    for (var i = 0; i < list.length; i++) {
        if (list[i][0] == '2') {
            if (rst.indexOf('2.4GHz') < 0) {
                rst.push('2.4GHz');
            }
        } else if (list[i][0] == '5') {
            if (rst.indexOf('5GHz') < 0) {
                rst.push('5GHz');
            }
        }
    }
    return rst
}

function render(ap) {
    var tags = $('<div class="wifi-tags"></div>')
    var encs = parse_enc(ap);
    for (var j = 0; j < encs.length; j++) {
        tags.append('<span class="tag enc">' + encs[j] + '</span>');
    }
    if (!ap.encrypted) {
        tags.children('span.enc').css('display', 'none');
    }
    var fres = parse_fre(ap);
    for (var k = 0; k < fres.length; k++) {
        tags.append('<span class="tag fre">' + fres[k] + '</span>');
    }
    var amp_img = (
        'images/wifi' + 
        ((ap.strength + 100) / 16).toFixed(0) + 
        (ap.encrypted ? '-lock' : '') + 
        '.png'
    );
    var btn = $(
        '<button class="btn btn-default ap"></button>'
    ).attr('id', 'ap-' + ap.ssid).append([
        $('<img class="signal">').attr('src', amp_img),
        $('<span class="ssid"></span>').text(ap.ssid.slice(0, 16)),
        tags,
    ]);
    if (ap.status == 'Connected') {
        btn.children('span.ssid').addClass('connected');
    }
    return $('<li></li>').append(btn);
}

function update_wifi_status() {
    $.ajax({
        method: 'GET',
        url: 'status',
        sucess: function (msg) {
            document.getElementById(
                'wifi-switch-checkbox'
            ).checked = (msg.wifi_state == 'enabled');
        }
    });
    var btn = $('#btn-refresh');
    var wc = $('#wifi-container');
    var ph = $('#nowifi-placeholder');
    if (wifi_enabled()) {
        btn.show();
        wc.show();
        ph.hide();
    } else {
        btn.hide();
        wc.hide();
        ph.show();
    }
}

function switch_wifi(obj) {
    $.ajax({
        method: "GET",
        url: "control",
        data: {
            action: obj.checked ? "enable" : "disable",
        },
    });
    update_wifi_status();
}

function pop_up(ap) {
    /* 
    example of an access point: {
        'ssid': u'BUAA-Mobile',
        'mac_address': '70:BA:EF:D2:49:52',
        'mode': 'infra',
        'encrypted': True,
        'frequency': ['2.462 GHz'],
        'encryption_type': ['key_mgmt_psk', 'pair_ccmp']
        'strength': -39,
        'quality': '30/70',
        'maxbitrate': '54 Mb/s',
        'saved': True,
        'status': 'Connected',
    }
    */
    if (!ap) return;
    if ($('#mask-ssid').text() == ap.ssid) {
        $('.mask').show();
        return;
    }

    $('#mask-ssid').text(ap.ssid);
    if (ap.saved) {
        $('#save-or-modify').text('Modify password');
        $('#forget-psk').show();
    } else {
        $('#save-or-modify').text('Save password');
        $('span[data-target="#psk-form-sub"]').click();
        $('#forget-psk').hide();
    }
    $('#wifi-info-sub').empty();
    $('.mask span[data-toggle="collapse"]').removeClass('fa-rotate-180').attr('aria-expanded', false);
    $('.mask .collapse').removeClass('show');
    var a = '<h3 class="info-attr"></h3>';
    var v = '<h3 class="info-value"></h3>';
    var attrs = [
        [$(a).text('Status'), $(v).text(ap.status)],
        [$(a).text('Security'), $(v).text(parse_enc(ap).join('/'))],
        [$(a).text('Signal'), $(v).text(ap.strength + 'dBm')],
        [$(a).text('Quality'), $(v).text(ap.quality)],
        [$(a).text('Frequency'), $(v).text(parse_fre(ap).join('/'))],
        [$(a).text('Speed'), $(v).text(ap.maxbitrate)],
        [$(a).text('MAC address'), $(v).text(ap.mac_address)],
    ];
    for (var i = 0; i < attrs.length; i++) {
        $('#wifi-info-sub').append(
            $('<li></li>').append(attrs[i])
        );
    }
    $('#input-user').attr('placeholder', 'e.g. bob');
    $('#input-psk').attr('placeholder', 'e.g. 12345678');
    $('.mask').show();
}