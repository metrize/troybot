let socket = null;
var open = false;
var stop_reload = false;

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
            JSON.stringify({
                event: 'AUTH',
                data: { access_token: auth.split(';')[1].split('&')[0] },
            })
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
        handleWebsocketData(json_data);
    };
    socket.onclose = function(e) {
        console.log(
            `WebSocket closed ${e.wasClean ? '' : 'un'}cleanly with reason ${
                e.code
            }: ${e.reason}`
        );
        socket = null;
        if (!stop_reload) {
            location.reload();
        } else {
            connect_to_ws();
        }
        stop_reload = false;
    };
}

function handleWebsocketData(json_data) {
    if (json_data['event'] === undefined) {
        return;
    }
    switch (json_data['event']) {
        case "initialize":
            initialize_player(json_data['data'])
            break;
    }
    console.log(json_data);
}

function initialize_player(data) {
    console.log(data)
}

$(document).ready(function() {
    connect_to_ws();
});

// 2. This code loads the IFrame Player API code asynchronously.
var tag = document.createElement('script');

tag.src = "https://www.youtube.com/iframe_api";
var firstScriptTag = document.getElementsByTagName('script')[0];
firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

var player;
function onYouTubeIframeAPIReady() {
  player = new YT.Player('player', {
    playerVars: { 'autoplay': 0, 'controls': 0, 'mute': 1},
    videoId: 'vXyLj-63jR0',
    events: {
      'onReady': onPlayerReady,
      'onStateChange': onPlayerStateChange
    }
  });
}

function onPlayerReady(event) {
    // event.target.playVideo();
}

var done = false;

function onPlayerStateChange(event) {
  if (event.data == YT.PlayerState.PLAYING) {
    $("#control_state").text("Pause");
    $("#volume div").css("width", player.getVolume()+"%");
    var playerTotalTime = player.getDuration();
    function timer() {
      var playerCurrentTime = player.getCurrentTime();
      var playerTimeDifference = (playerCurrentTime / playerTotalTime) * 100;
      var minutes = Math.floor(playerCurrentTime / 60);
      var seconds = Math.floor(playerCurrentTime - minutes * 60)
      $("#videotime div").css("width", playerTimeDifference+"%");
      $("#videocurrenttime").text(minutes+":"+('0'+seconds).slice(-2))
    }
    timer()
    mytimer = setInterval(timer, 1000);  
  } else {
    $("#control_state").text("Resume");
    try{
      clearTimeout(mytimer);
    } catch {
    }
  }
}

$("#control_state").on("click", function(e) {
    if (player.getPlayerState() == 1) {
        socket.send(
            JSON.stringify({
                event: 'PAUSE',
            })
        );
    } else {
        socket.send(
            JSON.stringify({
                event: 'RESUME',
            })
        );
    }
})

$("#control_previous").on("click", function(e) {
    socket.send(
        JSON.stringify({
            event: 'PREVIOUS',
        })
    );
})

$("#control_next").on("click", function(e) {
    socket.send(
        JSON.stringify({
            event: 'NEXT',
        })
    );
})

$("#videotime").on("click", function(e){
    socket.send(
        JSON.stringify({
            event: 'SEEK',
            data: { seek_time: player.getDuration() * ((e.pageX - $(this).offset().left) / $("#videotime").width()) },
        })
    );
})

$("#volume").on("click", function(e){
    JSON.stringify({
        event: 'VOLUME',
        data: { volume: ((e.pageX - $(this).offset().left) /  $("#volume").width())*100 },
    })
})

var currentqueuebody = $('#currentqueuebody')
currentqueuebody.sortable({
    placeholder: 'sortable-placeholder',
    items: 'tr',
    helper: function(e, tr) {
        var $originals = tr.children();
        var $helper = tr.clone();
        $helper.children().each(function(index) {
            // Set helper cell sizes to match the original sizes
            $(this).width($originals.eq(index).width());
        });
        return $helper;
    },
    start: function(evt, ui) {
        sourceIndex = $(ui.item).index();
    },
    stop: function(evt, ui) {
      console.log(sourceIndex + " to " + ui.item.index())
      socket.send(
          JSON.stringify({
              event: 'MOVE',
              data: {
                //   database_id: tracks[sourceIndex].database_id,
                  to_id: ui.item.index(),
              },
          })
      );
      setTimeout(function() {
        currentqueuebody.sortable('cancel');
      }, 0);
    },
});
