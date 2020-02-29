if (!String.prototype.format) {
    String.prototype.format = function() {
        var args = arguments;
        return this.replace(/{(\d+)}/g, function(match, number) {
            return typeof args[number] != 'undefined' ? args[number] : match;
        });
    };
}

$(document).ready(function() {
    connect_to_ws();
});

function add_random_box({ color }) {
    var divsize = 50;
    var posx = (Math.random() * ($(document).width() - divsize)).toFixed();
    var posy = (Math.random() * ($(document).height() - divsize)).toFixed();
    var $newdiv = $("<div class='exploding'></div>").css({
        left: posx + 'px',
        top: posy + 'px',
        'background-color': color,
        opacity: 0,
    });
    $newdiv.appendTo('body');
    $newdiv.animate(
        {
            opacity: 1,
        },
        500
    );
    setTimeout(function() {
        $newdiv.animate(
            {
                opacity: 0,
            },
            1000
        );
        setTimeout(function() {
            $newdiv.remove();
        }, 1000);
    }, 5000);
}

function getEmoteURL({ urls }) {
    let sortedSizes = Object.keys(urls)
        .map(size => parseInt(size))
        .sort();
    let largestSize = sortedSizes[sortedSizes.length - 1];
    return {
        url: urls[String(largestSize)],
        needsScale: 4 / largestSize,
    };
}

// opacity = number between 0 and 100
function add_emotes({
    emotes,
    opacity,
    persistence_time: persistenceTime,
    scale: emoteScale,
}) {
    for (let emote of emotes) {
        // largest URL available
        let { url, needsScale } = getEmoteURL(emote);

        let divsize = 120;
        let posx = (Math.random() * ($(document).width() - divsize)).toFixed();
        let posy = (Math.random() * ($(document).height() - divsize)).toFixed();
        let newdiv = $('<img class="absemote">').css({
            left: posx + 'px',
            top: posy + 'px',
            opacity: 0,
            transform: `scale(${(emoteScale / 100) * needsScale})`,
        });
        newdiv.attr({ src: url });
        newdiv.appendTo('body');
        newdiv.animate(
            {
                opacity: opacity / 100,
            },
            500
        );
        setTimeout(() => {
            newdiv.animate(
                {
                    opacity: 0,
                },
                1000
            );
            setTimeout(() => {
                newdiv.remove();
            }, 1000);
        }, persistenceTime);
    }
}

function show_custom_image(data) {
    var url = data.url;
    var divsize = 120;
    var posx = (Math.random() * ($(document).width() - divsize)).toFixed();
    var posy = (Math.random() * ($(document).height() - divsize)).toFixed();
    var css_data = {
        left: posx + 'px',
        top: posy + 'px',
        opacity: 0,
    };
    if (data.width !== undefined) {
        css_data.width = data.width;
    }
    if (data.height !== undefined) {
        css_data.height = data.height;
    }
    if (data.x !== undefined) {
        css_data.left = data.x + 'px';
    }
    if (data.y !== undefined) {
        css_data.top = data.y + 'px';
    }
    var $newdiv = $('<img class="absemote" src="' + url + '">').css(css_data);
    $newdiv.appendTo('body');
    $newdiv.animate(
        {
            opacity: 1,
        },
        500
    );
    setTimeout(function() {
        $newdiv.animate(
            {
                opacity: 0,
            },
            1000
        );
        setTimeout(function() {
            $newdiv.remove();
        }, 1000);
    }, 5000);
}

var message_id = 0;

function add_notification({ message }) {
    var new_notification = $('<div>' + message + '</div>').prependTo(
        'div.notifications'
    );
    new_notification.textillate({
        autostart: false,
        in: {
            effect: 'bounceInLeft',
            delay: 5,
            delayScale: 1.5,
            sync: false,
            shuffle: false,
            reverse: false,
        },
        out: {
            effect: 'bounceOutLeft',
            sync: true,
            shuffle: false,
            reverse: false,
        },
        type: 'word',
    });
    new_notification.on('inAnimationEnd.tlt', function() {
        setTimeout(function() {
            new_notification.textillate('out');
            new_notification.animate(
                {
                    height: 0,
                    opacity: 0,
                },
                1000
            );
        }, 2000);
    });
    new_notification.on('outAnimationEnd.tlt', function() {
        setTimeout(function() {
            new_notification.remove();
        }, 250);
    });
}

function refresh_combo_count(count) {
    $('#emote_combo span.count').html(count);
    $('#emote_combo span.count').addClass('animated pulsebig');
    $('#emote_combo span.count').on(
        'webkitAnimationEnd mozAnimationEnd MSAnimationEnd oanimationend animationend',
        function() {
            $(this).removeClass('animated pulsebig');
        }
    );
    $('#emote_combo img').addClass('animated pulsebig');
    $('#emote_combo img').on(
        'webkitAnimationEnd mozAnimationEnd MSAnimationEnd oanimationend animationend',
        function() {
            $(this).removeClass('animated pulsebig');
        }
    );
}

// https://gist.github.com/mkornblum/1384495
// slightly altered
$.fn.detachThenReattach = function(fn) {
    return this.each(function() {
        let $this = $(this);
        let tmpElement = $('<div style="display: none"/>');
        $this.after(tmpElement);
        $this.detach();
        fn.call($this);
        tmpElement.replaceWith($this);
    });
};

function refresh_combo_emote(emote) {
    let { url, needsScale } = getEmoteURL(emote);
    let $emoteCombo = $('#emote_combo img');

    // Fix for issue #378
    // we detach the <img> element from the DOM, then edit src and zoom,
    // then it is reattached where it used to be. This prevents the GIF animation
    // from resetting on all other emotes with the same URL on the screen
    $emoteCombo.detachThenReattach(function() {
        this.attr('src', url);
        this.css('zoom', String(needsScale));
    });
}

let current_emote_code = null;
let close_down_combo = null;

function refresh_emote_combo({ emote, count }) {
    let emote_combo = $('#emote_combo');
    if (emote_combo.length === 0) {
        current_emote_code = emote.code;
        let message = `x<span class="count">${count}</span> <img class="comboemote" /> combo!`;
        let new_notification = $(
            `<div id="emote_combo">${message}</div>`
        ).prependTo('div.notifications');
        new_notification.addClass('animated bounceInLeft');

        new_notification.on(
            'webkitAnimationEnd mozAnimationEnd MSAnimationEnd oanimationend animationend',
            function() {
                if (new_notification.hasClass('ended')) {
                    new_notification.animate(
                        {
                            height: 0,
                            opacity: 0,
                        },
                        500
                    );
                    setTimeout(function() {
                        new_notification.remove();
                    }, 500);
                }
            }
        );

        clearTimeout(close_down_combo);
        close_down_combo = setTimeout(function() {
            new_notification.addClass('animated bounceOutLeft ended');
        }, 4000);
    } else {
        clearTimeout(close_down_combo);
        close_down_combo = setTimeout(function() {
            emote_combo.addClass('animated bounceOutLeft ended');
        }, 3000);
    }

    refresh_combo_emote(emote);
    refresh_combo_count(count);
}

function play_sound({ link, volume }) {
    let player = new Howl({
        src: [link],
        volume: volume * 0.01, // the given volume is between 0 and 100
        onend: () => console.log('Playsound audio finished playing'),
        onloaderror: e => console.warn('audio load error', e),
        onplayerror: e => console.warn('audio play error', e),
    });

    player.play();
}

//Bet System
function bet_close_bet() {
    var bet_el = $('#bet');
    bet_el.fadeOut(5000, function() {
        bet_el.find('.left').css({
            visibility: 'hidden',
            opacity: 1,
        });
    });
    bet_el.hide();
}
function bet_show_bets() {
    var bet_el = $('#bet');
    bet_el.find('.left').css({
        visibility: 'visible',
        opacity: 1,
    });
    bet_el.find('.left').show();
    bet_el.show();
}
function bet_update_data({
    win_betters,
    loss_betters,
    win_points,
    loss_points,
}) {
    $('#winbetters').text(win_betters);
    $('#lossbetters').text(loss_betters);
    $('#winpoints').text(win_points);
    $('#losspoints').text(loss_points);
}
function bet_new_game() {
    var bet_el = $('#bet');
    bet_el.find('.left').css({
        visibility: 'visible',
        opacity: 1,
    });

    bet_el.hide();

    $('#winbetters').text('0');
    $('#lossbetters').text('0');
    $('#winpoints').text('0');
    $('#losspoints').text('0');

    bet_el.find('.left').show();
    bet_el.fadeIn(1000, function() {
        console.log('Faded in');
    });
}
function bet_reload() {
    var bet_el = $('#bet');
    bet_el.find('.left').css({
        visibility: 'hidden',
        opacity: 1,
    });
    bet_el.hide();
    $('#winbetters').text('0');
    $('#lossbetters').text('0');
    $('#winpoints').text('0');
    $('#losspoints').text('0');
}

function handleWebsocketData(json_data) {
    if (json_data['event'] === undefined) {
        return;
    }

    let data = json_data.data;
    switch (json_data['event']) {
        case 'notification':
            add_notification(data);
            break;
        case 'new_emotes':
            add_emotes(data);
            break;
        case 'play_sound':
            play_sound(data);
            break;
        case 'emote_combo':
            refresh_emote_combo(data);
            break;
        case 'bet_new_game':
            bet_new_game();
            break;
        case 'bet_show_bets':
            bet_show_bets();
            break;
        case 'bet_update_data':
            bet_update_data(data);
            break;
        case 'bet_close_game':
            bet_close_bet();
            break;
        case 'show_custom_image':
            show_custom_image(data);
            break;
        case 'refresh':
        case 'reload':
            bet_reload();
            break;
        case 'songrequest_play':
            play(data);
            break;
        case 'songrequest_pause':
            pause();
            break;
        case 'songrequest_resume':
            resume();
            break;
        case 'songrequest_volume':
            volume(data);
            break;
        case 'songrequest_seek':
            seek(data);
            break;
        case 'songrequest_show':
            show();
            break;
        case 'songrequest_hide':
            hide();
            break;
        case 'songrequest_stop':
            stop();
            break;
    }
}

function adblocker() {
    $(".video-ads").classList.add("hide_vid")
}

// 2. This code loads the IFrame Player API code asynchronously.
var tag = document.createElement('script');

tag.src = "https://www.youtube.com/iframe_api";
var firstScriptTag = document.getElementsByTagName('script')[0];
firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

var player;
function onYouTubeIframeAPIReady() {
  player = new YT.Player('player', {
    playerVars: { 'autoplay': 0, 'controls': 0},
    videoId: '',
    events: {
      'onStateChange': onPlayerStateChange
    }
  });
}

function onPlayerStateChange(event) {
    adblocker()
    if (event.data == 0) {
        hide()
        socket.send(
            JSON.stringify({
                event: 'next_song',
                data: { salt: salt_value },
            })
        );
    }
}

function play({ video_id }) {
    player.loadVideoById(video_id);
    player.pauseVideo();
    socket.send(
        JSON.stringify({ event: 'ready', data: { salt: salt_value } })
    );
}

function pause() {
    player.pauseVideo();
}

function resume() {
    player.playVideo();
}

function seek({ seek_time }) {
    player.seekTo(seek_time);
    pause();
    socket.send(JSON.stringify({ event: 'ready', data: { salt: salt_value } }));
}

function volume({ volume }) {
    player.setVolume(volume);
}

function hide() {
    $('#songrequest').hide();
}

function show() {
    $('#songrequest').show();
}

function stop() {
    player.loadVideoById("");
    player.stopVideo();
}

let socket = null;

function connect_to_ws() {
    if (socket != null) {
        return;
    }

    console.log('Connecting to websocket....');
    socket = new WebSocket(ws_host);
    socket.binaryType = 'arraybuffer';
    socket.onopen = function() {
        console.log('WebSocket Connected!');
        socket.send(
            JSON.stringify({ event: 'auth', data: { salt: salt_value } })
        );
    };
    socket.onerror = function(event) {
        console.error('WebSocket error observed:', event);
    };
    socket.onmessage = function(e) {
        if (typeof e.data != 'string') {
            return;
        }
        let json_data = JSON.parse(e.data);
        console.log('Received data:', json_data);
        handleWebsocketData(json_data);
    };
    socket.onclose = function(e) {
        console.log(
            `WebSocket closed ${e.wasClean ? '' : 'un'}cleanly with reason ${
                e.code
            }: ${e.reason}`
        );
        socket = null;
        location.reload(true);
    };
}
