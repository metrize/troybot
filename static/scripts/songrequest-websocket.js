let socket = null;
var open = false;

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
        connect_to_ws();
    };
}

function handleWebsocketData(json_data) {
    if (json_data['event'] === undefined) {
        return;
    }
    console.log(json_data);
    switch (json_data['event']) {
        case 'initialize':
            initialize_player(json_data['data']);
            break;
        case 'play':
            current_song(json_data['data']);
            break;
        case 'volume':
            set_volume(json_data['data']);
            break;
        case 'playlist':
            set_playlist(json_data['data']);
            break;
        case 'backup_playlist':
            set_backup_playlist(json_data['data']);
            break;
        case 'history_list':
            set_history_list(json_data['data']);
            break;
        case 'favourite_list':
            set_favourite_list(json_data['data']);
            break;
        case 'banned_list':
            set_banned_list(json_data['data']);
            break;
        case 'module_state':
            set_module_state(json_data['data']);
            break;
    }
}
var paused = false;
var video_showing = false;
var enabled = false;
var requests_open = false;
var use_backup_playlist = false;

function current_song(data) {
    if (Object.keys(data['current_song']).length === 0) {
        $('#status').text('No songs currently playing!');
        $('#songname').hide();
        $('#url').hide();
        player.loadVideoById('');
        player.stopVideo();
    } else {
        player.stopVideo();
        $('#status').text(
            'Now Playing - ' + data['current_song']['requested_by']
        );
        $('#songname').show();
        $('#url').show();
        $('#song_title').text(data['current_song']['song_info']['title']);
        $('#url a').text(
            'https://www.youtube.com/watch?v=' +
                data['current_song']['song_info']['video_id']
        );
        $('#url a').attr(
            'href',
            'https://www.youtube.com/watch?v=' +
                data['current_song']['song_info']['video_id']
        );
        console.log(
            Math.round(
                data['current_song']['current_song_time'] +
                    Math.floor(new Date().getTime() / 1000) -
                    parseFloat(data['current_timestamp']) +
                    0.5,
                2
            )
        );
        player.loadVideoById(
            data['current_song']['song_info']['video_id'],
            Math.round(
                data['current_song']['current_song_time'] +
                    Math.floor(new Date().getTime() / 1000) -
                    parseFloat(data['current_timestamp']) +
                    0.5,
                2
            )
        );
    }
}

function set_volume(data) {
    player.setVolume(data['volume']);
    $('#volume div').css('width', data['volume'] + '%');
}

function set_playlist(data) {
    $('#currentqueuebody').empty();
    data['playlist'].forEach(function(song) {
        $('#currentqueuebody').append(
            `<tr data-id="` +
                song['database_id'] +
                `" data-favourite=` +
                song['song_info']['favourite'] +
                ` data-banned=` +
                song['song_info']['banned'] +
                `>
      <td>
        <div class="d-flex justify-content-between">
          <div class="p-2 align-self-center">
            <svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" width="48px" height="28px" viewBox="0 0 48 28" enable-background="new 0 0 48 28" xml:space="preserve">  <image id="image0" width="48" height="28" x="0" y="0"
              href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAcAgMAAABaAtRZAAAABGdBTUEAALGPC/xhBQAAACBjSFJN
              AAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAADFBMVEX///8AAABUbnr///9N
              redqAAAAAnRSTlMAAHaTzTgAAAABYktHRACIBR1IAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJ
              TUUH5AIbBR8yv5/tPwAAAB5JREFUGNNjYCAHcK2CggXEc1hDoSCAeM5gtod0AADW6V+h4CpCKgAA
              ACV0RVh0ZGF0ZTpjcmVhdGUAMjAyMC0wMi0yN1QxMjozMTo1MC0wNzowMNnwhHMAAAAldEVYdGRh
              dGU6bW9kaWZ5ADIwMjAtMDItMjdUMTI6MzE6NTAtMDc6MDCorTzPAAAAAElFTkSuQmCC" />
            </svg>
          </div>
          <div class="p-2 align-self-center">
            <div class="d-flex flex-column">
              <div class="p-2">
                <span><a>` +
                song['song_info']['title'] +
                `</a> Duration ` +
                song['formatted_duration'] +
                `</span>
              </div>
              <div class="p-2">
                <span>-Requested By ` +
                song['requested_by'] +
                `</span>
              </div>
            </div>
          </div>
          <div class="ml-auto p-2 align-self-center">
            <div class="dropdown dropleft">
              <a class="" href="#" role="button" id="dropdownMenuLink" data-toggle="dropdown">
                <svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" width="40px" height="40px" viewBox="0 0 40 40" enable-background="new 0 0 40 40" xml:space="preserve">  <image id="image0" width="40" height="40" x="0" y="0"
                  href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACgAAAAoCAMAAAC7IEhfAAAABGdBTUEAALGPC/xhBQAAACBjSFJN
              AAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAAV1BMVEUAAAAAAAAtDwwrDgsu
              DwzAPzGVMSctDgssDwyOLyXDQTMuEAsAAADCQDOOLyUsDguNLyWUMSYuDguPMCUoDgyOLyWQMCWP
              LyUAAADCQTMuEAznTDz///8dVoCNAAAAG3RSTlMAA65wrPnrcWnq+7IE++tv6etw623p6+oC+7Ho
              kTMcAAAAAWJLR0QcnARBBwAAAAd0SU1FB+QCGwUtHmA31a0AAADWSURBVDjLxdTdFoIgDADgiWVa
              KZL2y/u/ZwZBDLbVVe7KA587nrkNYO2oVE1f1KpCbrNtdpRru/3hiJy1lGw7axPpHCVfLpWqty6G
              7Dv14M97FV4c/UGW0+dbwpxAkoQjJekIybhCsi6T0TWFQ1J0S9mm9/UQHiZNN0DMKeYrJe+wlBzA
              fA7uIjqYr7/BWBdL9yflJIkdL2PBJ7ngyX9jOrlwbM8XTpBFv3ybo+a/c/RZAFnZQmHjArj5lcLN
              0f0Rl4+ThpmjxDlpyLZqR+SERarxIl0lnra6MGBtol6jAAAAJXRFWHRkYXRlOmNyZWF0ZQAyMDIw
              LTAyLTI3VDEyOjQ1OjMwLTA3OjAwP084DQAAACV0RVh0ZGF0ZTptb2RpZnkAMjAyMC0wMi0yN1Qx
              Mjo0NTozMC0wNzowME4SgLEAAAAASUVORK5CYII=" />
              </svg>
              </a>
            
              <div class="dropdown-menu" aria-labelledby="dropdownMenuLink">
                <a onclick="ban_control.call(this,event)" class="dropdown-item" href="#">` +
                (song['song_info']['banned'] ? 'Unban' : 'Ban') +
                `</a>
                <a onclick="delete_control.call(this,event)" class="dropdown-item" href="#">Delete</a>
              </div>
            </div>
          </div>
          <div class="p-2 align-self-center">` +
                (song['song_info']['favourite']
                    ? `
              <svg onclick="favourite_control.call(this,event)" version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" width="44px" height="36px" viewBox="0 0 44 36" enable-background="new 0 0 44 36" xml:space="preserve">  <image id="image0" width="44" height="36" x="0" y="0"
                  href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACwAAAAkCAMAAADFCSheAAAABGdBTUEAALGPC/xhBQAAACBjSFJN
              AAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAB7FBMVEUAAAAAAAAAAAAAAAAA
              AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
              AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
              AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
              AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
              AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABjIBqnNyvEQDPdSTngSjrPRDam
              NytrIxxsIxzQRTZiIBl4KB/kSzvnTDx5KCB6KCB4Jx+oNyyuOS2wOi7FQTPGQTTDQDOvOi3bSDl3
              Jx9kIRphIBmkNivcSDnaSDnZSDjBPzLAPzKaMyhSGxXeSTpzJh51Jh69PjHCQDJeHxh0Jh6QLyWV
              MSelNiuyOy68PjG6PTCZMiijNiqHLCOUMSZ8KSCBKiFmIhviSzttJBxUHBazOy9fHxmILSOMLiTT
              RTfmTDxpIxuSMCbiSjt9KSB+KSH////VIxNvAAAAXXRSTlMAHm242PT35bd2ICF35mwdHJ38paac
              G1Dz8ldZTm/9/nByblganptrtdvx8NXUqlsP9RGKjBYYaAG9xAIX4+g2+TxN+1xmZEBLLO060SUI
              ka1d+C0yBYCZCziysyKU6NSiAAAAAWJLR0Sjx9rvGgAAAAd0SU1FB+QCHAMoD+6qRREAAAG8SURB
              VDjLY2CAAEYmZhZWNnYOTi4GOODmYeZlY2Vh5uNnQAYCgkKxcfEJiUnJKULCUClGEaHUuLTEhPi4
              dCFRMYRacYmMzCwoyMyWlAKJSUvkIMRyJWVgamXl8rKQQL68AgODonwBsliynBLUXLn4LBRQKC+l
              LF+EKlYsBzZbQCIvCw3kS0qWoIslS6oAFatmZGGA0lJMsTI1oKeFMrOIAplCAgxK5cSpzcqqUGfg
              SCZWcaUGg2YRsYrjWRgkqohVXCXBoFVNrOIabQadWmIV1+ky6NUTq7hej0G/gVjFDfoMBsT6sNHQ
              iIHBuIk4xc0mwLRhKtlCjNpWVjNQsjNvI0ZxBRM4PVtYthNWm21lDUn9NrYdhNR22sEzrT1bF361
              JQ6OiBzr5NyNT22PnDJyWeAil4dbba+8K0rBwSDO1odLbb+QGwMacNeegF3tRFYPBgzgaTsJm9rJ
              Xt4MWACXz5SpGGqnsfgyYAV+/tNnoCqNnxlgwIALBLLOQlY7O0iWAQ8I1i2fA1M6dx5LCANeEBom
              NB8aw/LhEQyEQCRLObCgXDBP05GgUpDhshILFzn4EzYWArijomOwiQMALzHEeJ02LUgAAAAldEVY
              dGRhdGU6Y3JlYXRlADIwMjAtMDItMjhUMTA6NDA6MTUtMDc6MDAnzQniAAAAJXRFWHRkYXRlOm1v
              ZGlmeQAyMDIwLTAyLTI4VDEwOjQwOjE1LTA3OjAwVpCxXgAAAABJRU5ErkJggg==" />
              </svg>
      `
                    : `
            <svg onclick="favourite_control.call(this,event)" version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" width="44px" height="36px" viewBox="0 0 44 36" enable-background="new 0 0 44 36" xml:space="preserve">  <image id="image0" width="44" height="36" x="0" y="0"
              href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACwAAAAkCAQAAABY3hDnAAAABGdBTUEAALGPC/xhBQAAACBjSFJN
          AAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAAAmJLR0QA/4ePzL8AAAAHdElN
          RQfkAhsFOBnJ5qYaAAACPElEQVRIx62WPWhTURiGn9x0soJOlkAnJ/EHpTRF6uKsm5MopYtLEUEI
          FBzaguAgIoYGoaVUInYRukjioA6iDbEUdXCq0hBpJW0URL2nTUvvva9DrW3T/Nwk95lfnvNyz3fO
          PSH2EuUqPXTQQZhf5PlEkln200s/pzjKIVyKFJljivdUoYs0TlxZ5WRU0rKyGhMOL+guW/wlzriy
          WlFJRjllFRcOac5U0g5iJuSoHEeTwmbof24E86hiblzYxMq1Cdy8qlEQHgkAHuKtVM0tCJfRvW1d
          R7VwhMcQw3hezdymcHdad2HyqkdB2NjLdXMLwub0lvj5RN24JNmyfeXGRApCRHnnhMMEh0ubS49F
          32igWgjzIEyfRXd3664yohC1iEQCF0cgEsKY9vaAxascXLXwvMAbu+BaFIuBi4tQtFhcDFy8BEsW
          mUzg4gxkQnQyH+z2rdG+xgmLb6QmA+2bhBRfAY5h+7sF/GCE4eT2IvevBya+IeI77S3mEoFoJ8VH
          2nZ/mOMU3rSsnRXf2Xf1XKa00JJ2WWzQX2k7Y2z+aFprhMtwtUm5XeuXWos/wuNerSEcpPShYe1n
          4XC33nxf43eqIW1WGG76OToXKDz2rX0qftLn91SeZf6WL+0dkeN8Iwf+MNMDqj0j6xoQr+lsRLs9
          IyZdVftKrP97djXBRb7EKjwAPY2IHJea1QIcIIkzs0c7KzyecaQV7RZXyMVkJEkbGhH5yge3ud4J
          zBNNiQ2mg+i6m17eMsM5v/G/N+7KqQlAhuoAAAAldEVYdGRhdGU6Y3JlYXRlADIwMjAtMDItMjdU
          MTI6NTY6MjUtMDc6MDCLZHP3AAAAJXRFWHRkYXRlOm1vZGlmeQAyMDIwLTAyLTI3VDEyOjU2OjI1
          LTA3OjAw+jnLSwAAAABJRU5ErkJggg==" />
          </svg>`) +
                `
          
          </div>
        </div>
      </td>
    </tr>`
        );
    });
}

function set_backup_playlist(data) {
    $('#backupqueuebody').empty();
    data['backup_playlist'].forEach(function(song) {
        $('#backupqueuebody').append(
            `<tr data-id="` +
                song['database_id'] +
                `" data-favourite=` +
                song['song_info']['favourite'] +
                ` data-banned=` +
                song['song_info']['banned'] +
                `>
      <td>
        <div class="d-flex justify-content-between">
          <div class="p-2 align-self-center">
            <svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" width="48px" height="28px" viewBox="0 0 48 28" enable-background="new 0 0 48 28" xml:space="preserve">  <image id="image0" width="48" height="28" x="0" y="0"
              href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAcAgMAAABaAtRZAAAABGdBTUEAALGPC/xhBQAAACBjSFJN
              AAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAADFBMVEX///8AAABUbnr///9N
              redqAAAAAnRSTlMAAHaTzTgAAAABYktHRACIBR1IAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJ
              TUUH5AIbBR8yv5/tPwAAAB5JREFUGNNjYCAHcK2CggXEc1hDoSCAeM5gtod0AADW6V+h4CpCKgAA
              ACV0RVh0ZGF0ZTpjcmVhdGUAMjAyMC0wMi0yN1QxMjozMTo1MC0wNzowMNnwhHMAAAAldEVYdGRh
              dGU6bW9kaWZ5ADIwMjAtMDItMjdUMTI6MzE6NTAtMDc6MDCorTzPAAAAAElFTkSuQmCC" />
            </svg>
          </div>
          <div class="p-2 align-self-center">
            <div class="d-flex flex-column">
              <div class="p-2">
                <span><a>` +
                song['song_info']['title'] +
                `</a> Duration ` +
                song['formatted_duration'] +
                `</span>
              </div>
              <div class="p-2">
                <span>-Requested By ` +
                song['requested_by'] +
                `</span>
              </div>
            </div>
          </div>
          <div class="ml-auto p-2 align-self-center">` +
                (song['song_info']['favourite']
                    ? `
              <svg onclick="favourite_control.call(this,event)" version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" width="44px" height="36px" viewBox="0 0 44 36" enable-background="new 0 0 44 36" xml:space="preserve">  <image id="image0" width="44" height="36" x="0" y="0"
                  href="data:image/png;base64,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" />
              </svg>
      `
                    : `
            <svg onclick="favourite_control.call(this,event)" version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" width="44px" height="36px" viewBox="0 0 44 36" enable-background="new 0 0 44 36" xml:space="preserve">  <image id="image0" width="44" height="36" x="0" y="0"
              href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACwAAAAkCAQAAABY3hDnAAAABGdBTUEAALGPC/xhBQAAACBjSFJN
          AAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAAAmJLR0QA/4ePzL8AAAAHdElN
          RQfkAhsFOBnJ5qYaAAACPElEQVRIx62WPWhTURiGn9x0soJOlkAnJ/EHpTRF6uKsm5MopYtLEUEI
          FBzaguAgIoYGoaVUInYRukjioA6iDbEUdXCq0hBpJW0URL2nTUvvva9DrW3T/Nwk95lfnvNyz3fO
          PSH2EuUqPXTQQZhf5PlEkln200s/pzjKIVyKFJljivdUoYs0TlxZ5WRU0rKyGhMOL+guW/wlzriy
          WlFJRjllFRcOac5U0g5iJuSoHEeTwmbof24E86hiblzYxMq1Cdy8qlEQHgkAHuKtVM0tCJfRvW1d
          R7VwhMcQw3hezdymcHdad2HyqkdB2NjLdXMLwub0lvj5RN24JNmyfeXGRApCRHnnhMMEh0ubS49F
          32igWgjzIEyfRXd3664yohC1iEQCF0cgEsKY9vaAxascXLXwvMAbu+BaFIuBi4tQtFhcDFy8BEsW
          mUzg4gxkQnQyH+z2rdG+xgmLb6QmA+2bhBRfAY5h+7sF/GCE4eT2IvevBya+IeI77S3mEoFoJ8VH
          2nZ/mOMU3rSsnRXf2Xf1XKa00JJ2WWzQX2k7Y2z+aFprhMtwtUm5XeuXWos/wuNerSEcpPShYe1n
          4XC33nxf43eqIW1WGG76OToXKDz2rX0qftLn91SeZf6WL+0dkeN8Iwf+MNMDqj0j6xoQr+lsRLs9
          IyZdVftKrP97djXBRb7EKjwAPY2IHJea1QIcIIkzs0c7KzyecaQV7RZXyMVkJEkbGhH5yge3ud4J
          zBNNiQ2mg+i6m17eMsM5v/G/N+7KqQlAhuoAAAAldEVYdGRhdGU6Y3JlYXRlADIwMjAtMDItMjdU
          MTI6NTY6MjUtMDc6MDCLZHP3AAAAJXRFWHRkYXRlOm1vZGlmeQAyMDIwLTAyLTI3VDEyOjU2OjI1
          LTA3OjAw+jnLSwAAAABJRU5ErkJggg==" />
          </svg>`) +
                `
          
          </div>
        </div>
      </td>
    </tr>`
        );
    });
}

function set_history_list(data) {
    $('#historybody').empty();
    data['history_list'].forEach(function(song) {
        $('#historybody').append(
            `<tr data-histid="` +
                song['database_id'] +
                `" data-favourite=` +
                song['song_info']['favourite'] +
                ` data-banned=` +
                song['song_info']['banned'] +
                `>
      <td>
        <div class="d-flex justify-content-between">
          <div class="p-2 align-self-center">
            <svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" width="48px" height="28px" viewBox="0 0 48 28" enable-background="new 0 0 48 28" xml:space="preserve">  <image id="image0" width="48" height="28" x="0" y="0"
              href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAcAgMAAABaAtRZAAAABGdBTUEAALGPC/xhBQAAACBjSFJN
              AAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAADFBMVEX///8AAABUbnr///9N
              redqAAAAAnRSTlMAAHaTzTgAAAABYktHRACIBR1IAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJ
              TUUH5AIbBR8yv5/tPwAAAB5JREFUGNNjYCAHcK2CggXEc1hDoSCAeM5gtod0AADW6V+h4CpCKgAA
              ACV0RVh0ZGF0ZTpjcmVhdGUAMjAyMC0wMi0yN1QxMjozMTo1MC0wNzowMNnwhHMAAAAldEVYdGRh
              dGU6bW9kaWZ5ADIwMjAtMDItMjdUMTI6MzE6NTAtMDc6MDCorTzPAAAAAElFTkSuQmCC" />
            </svg>
          </div>
          <div class="p-2 align-self-center">
            <div class="d-flex flex-column">
              <div class="p-2">
                <span><a>` +
                song['song_info']['title'] +
                `</a> Played for ` +
                song['formatted_duration'] +
                `</span>
              </div>
              <div class="p-2">
                <span>-Requested By ` +
                song['requested_by'] +
                `</span>
              </div>
            </div>
          </div>
          <div class="ml-auto p-2 align-self-center">
            <div class="dropdown dropleft">
              <a class="" href="#" role="button" id="dropdownMenuLink" data-toggle="dropdown">
                <svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" width="40px" height="40px" viewBox="0 0 40 40" enable-background="new 0 0 40 40" xml:space="preserve">  <image id="image0" width="40" height="40" x="0" y="0"
                  href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACgAAAAoCAMAAAC7IEhfAAAABGdBTUEAALGPC/xhBQAAACBjSFJN
              AAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAAV1BMVEUAAAAAAAAtDwwrDgsu
              DwzAPzGVMSctDgssDwyOLyXDQTMuEAsAAADCQDOOLyUsDguNLyWUMSYuDguPMCUoDgyOLyWQMCWP
              LyUAAADCQTMuEAznTDz///8dVoCNAAAAG3RSTlMAA65wrPnrcWnq+7IE++tv6etw623p6+oC+7Ho
              kTMcAAAAAWJLR0QcnARBBwAAAAd0SU1FB+QCGwUtHmA31a0AAADWSURBVDjLxdTdFoIgDADgiWVa
              KZL2y/u/ZwZBDLbVVe7KA587nrkNYO2oVE1f1KpCbrNtdpRru/3hiJy1lGw7axPpHCVfLpWqty6G
              7Dv14M97FV4c/UGW0+dbwpxAkoQjJekIybhCsi6T0TWFQ1J0S9mm9/UQHiZNN0DMKeYrJe+wlBzA
              fA7uIjqYr7/BWBdL9yflJIkdL2PBJ7ngyX9jOrlwbM8XTpBFv3ybo+a/c/RZAFnZQmHjArj5lcLN
              0f0Rl4+ThpmjxDlpyLZqR+SERarxIl0lnra6MGBtol6jAAAAJXRFWHRkYXRlOmNyZWF0ZQAyMDIw
              LTAyLTI3VDEyOjQ1OjMwLTA3OjAwP084DQAAACV0RVh0ZGF0ZTptb2RpZnkAMjAyMC0wMi0yN1Qx
              Mjo0NTozMC0wNzowME4SgLEAAAAASUVORK5CYII=" />
              </svg>
              </a>
            
              <div class="dropdown-menu" aria-labelledby="dropdownMenuLink">
                <a onclick="ban_control.call(this,event)" class="dropdown-item" href="#">` +
                (song['song_info']['banned'] ? 'Unban' : 'Ban') +
                `</a>
              </div>
            </div>
          </div>
          <div class="p-2 align-self-center">` +
                (song['song_info']['favourite']
                    ? `
              <svg onclick="favourite_control.call(this,event)" version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" width="44px" height="36px" viewBox="0 0 44 36" enable-background="new 0 0 44 36" xml:space="preserve">  <image id="image0" width="44" height="36" x="0" y="0"
                  href="data:image/png;base64,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" />
              </svg>
      `
                    : `
            <svg onclick="favourite_control.call(this,event)" version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" width="44px" height="36px" viewBox="0 0 44 36" enable-background="new 0 0 44 36" xml:space="preserve">  <image id="image0" width="44" height="36" x="0" y="0"
              href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACwAAAAkCAQAAABY3hDnAAAABGdBTUEAALGPC/xhBQAAACBjSFJN
          AAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAAAmJLR0QA/4ePzL8AAAAHdElN
          RQfkAhsFOBnJ5qYaAAACPElEQVRIx62WPWhTURiGn9x0soJOlkAnJ/EHpTRF6uKsm5MopYtLEUEI
          FBzaguAgIoYGoaVUInYRukjioA6iDbEUdXCq0hBpJW0URL2nTUvvva9DrW3T/Nwk95lfnvNyz3fO
          PSH2EuUqPXTQQZhf5PlEkln200s/pzjKIVyKFJljivdUoYs0TlxZ5WRU0rKyGhMOL+guW/wlzriy
          WlFJRjllFRcOac5U0g5iJuSoHEeTwmbof24E86hiblzYxMq1Cdy8qlEQHgkAHuKtVM0tCJfRvW1d
          R7VwhMcQw3hezdymcHdad2HyqkdB2NjLdXMLwub0lvj5RN24JNmyfeXGRApCRHnnhMMEh0ubS49F
          32igWgjzIEyfRXd3664yohC1iEQCF0cgEsKY9vaAxascXLXwvMAbu+BaFIuBi4tQtFhcDFy8BEsW
          mUzg4gxkQnQyH+z2rdG+xgmLb6QmA+2bhBRfAY5h+7sF/GCE4eT2IvevBya+IeI77S3mEoFoJ8VH
          2nZ/mOMU3rSsnRXf2Xf1XKa00JJ2WWzQX2k7Y2z+aFprhMtwtUm5XeuXWos/wuNerSEcpPShYe1n
          4XC33nxf43eqIW1WGG76OToXKDz2rX0qftLn91SeZf6WL+0dkeN8Iwf+MNMDqj0j6xoQr+lsRLs9
          IyZdVftKrP97djXBRb7EKjwAPY2IHJea1QIcIIkzs0c7KzyecaQV7RZXyMVkJEkbGhH5yge3ud4J
          zBNNiQ2mg+i6m17eMsM5v/G/N+7KqQlAhuoAAAAldEVYdGRhdGU6Y3JlYXRlADIwMjAtMDItMjdU
          MTI6NTY6MjUtMDc6MDCLZHP3AAAAJXRFWHRkYXRlOm1vZGlmeQAyMDIwLTAyLTI3VDEyOjU2OjI1
          LTA3OjAw+jnLSwAAAABJRU5ErkJggg==" />
          </svg>`) +
                `
          
          </div>
        </div>
      </td>
    </tr>`
        );
    });
}

function set_favourite_list(data) {
    $('#favouritelist').empty();
    data['favourite_list'].forEach(function(song_info) {
        $('#favouritelist').append(
            `<tr data-infoid="` +
                song_info['video_id'] +
                `" data-favourite=` +
                song_info['favourite'] +
                ` data-banned=` +
                song_info['banned'] +
                `>
      <td>
        <div class="d-flex justify-content-between">
          <div class="p-2 align-self-center">
            <svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" width="48px" height="28px" viewBox="0 0 48 28" enable-background="new 0 0 48 28" xml:space="preserve">  <image id="image0" width="48" height="28" x="0" y="0"
              href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAcAgMAAABaAtRZAAAABGdBTUEAALGPC/xhBQAAACBjSFJN
              AAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAADFBMVEX///8AAABUbnr///9N
              redqAAAAAnRSTlMAAHaTzTgAAAABYktHRACIBR1IAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJ
              TUUH5AIbBR8yv5/tPwAAAB5JREFUGNNjYCAHcK2CggXEc1hDoSCAeM5gtod0AADW6V+h4CpCKgAA
              ACV0RVh0ZGF0ZTpjcmVhdGUAMjAyMC0wMi0yN1QxMjozMTo1MC0wNzowMNnwhHMAAAAldEVYdGRh
              dGU6bW9kaWZ5ADIwMjAtMDItMjdUMTI6MzE6NTAtMDc6MDCorTzPAAAAAElFTkSuQmCC" />
            </svg>
          </div>
          <div class="p-2 align-self-center">
            <div class="d-flex flex-column">
              <div class="p-2">
                <span><a>` +
                song_info['title'] +
                `</a> Duration: ` +
                song_info['formatted_duration'] +
                `</span>
              </div>
            </div>
          </div>
          <div class="ml-auto p-2 align-self-center">
            <div class="dropdown dropleft">
              <a class="" href="#" role="button" id="dropdownMenuLink" data-toggle="dropdown">
                <svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" width="40px" height="40px" viewBox="0 0 40 40" enable-background="new 0 0 40 40" xml:space="preserve">  <image id="image0" width="40" height="40" x="0" y="0"
                  href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACgAAAAoCAMAAAC7IEhfAAAABGdBTUEAALGPC/xhBQAAACBjSFJN
              AAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAAV1BMVEUAAAAAAAAtDwwrDgsu
              DwzAPzGVMSctDgssDwyOLyXDQTMuEAsAAADCQDOOLyUsDguNLyWUMSYuDguPMCUoDgyOLyWQMCWP
              LyUAAADCQTMuEAznTDz///8dVoCNAAAAG3RSTlMAA65wrPnrcWnq+7IE++tv6etw623p6+oC+7Ho
              kTMcAAAAAWJLR0QcnARBBwAAAAd0SU1FB+QCGwUtHmA31a0AAADWSURBVDjLxdTdFoIgDADgiWVa
              KZL2y/u/ZwZBDLbVVe7KA587nrkNYO2oVE1f1KpCbrNtdpRru/3hiJy1lGw7axPpHCVfLpWqty6G
              7Dv14M97FV4c/UGW0+dbwpxAkoQjJekIybhCsi6T0TWFQ1J0S9mm9/UQHiZNN0DMKeYrJe+wlBzA
              fA7uIjqYr7/BWBdL9yflJIkdL2PBJ7ngyX9jOrlwbM8XTpBFv3ybo+a/c/RZAFnZQmHjArj5lcLN
              0f0Rl4+ThpmjxDlpyLZqR+SERarxIl0lnra6MGBtol6jAAAAJXRFWHRkYXRlOmNyZWF0ZQAyMDIw
              LTAyLTI3VDEyOjQ1OjMwLTA3OjAwP084DQAAACV0RVh0ZGF0ZTptb2RpZnkAMjAyMC0wMi0yN1Qx
              Mjo0NTozMC0wNzowME4SgLEAAAAASUVORK5CYII=" />
              </svg>
              </a>
            
              <div class="dropdown-menu" aria-labelledby="dropdownMenuLink">
                <a onclick="ban_control.call(this,event)" class="dropdown-item" href="#">` +
                (song_info['banned'] ? 'Unban' : 'Ban') +
                `</a>
              </div>
            </div>
          </div>
          <div class="p-2 align-self-center">
              <svg onclick="favourite_control.call(this,event)" version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" width="44px" height="36px" viewBox="0 0 44 36" enable-background="new 0 0 44 36" xml:space="preserve">  <image id="image0" width="44" height="36" x="0" y="0"
                  href="data:image/png;base64,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" />
              </svg>
          </div>
        </div>
      </td>
    </tr>`
        );
    });
}

function set_banned_list(data) {
    $('#bannedlist').empty();
    data['banned_list'].forEach(function(song_info) {
        $('#bannedlist').append(
            `<tr data-infoid="` +
                song_info['video_id'] +
                `" data-favourite=` +
                song_info['favourite'] +
                ` data-banned=` +
                song_info['banned'] +
                `>
      <td>
        <div class="d-flex justify-content-between">
          <div class="p-2 align-self-center">
            <svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" width="48px" height="28px" viewBox="0 0 48 28" enable-background="new 0 0 48 28" xml:space="preserve">  <image id="image0" width="48" height="28" x="0" y="0"
              href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAcAgMAAABaAtRZAAAABGdBTUEAALGPC/xhBQAAACBjSFJN
              AAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAADFBMVEX///8AAABUbnr///9N
              redqAAAAAnRSTlMAAHaTzTgAAAABYktHRACIBR1IAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJ
              TUUH5AIbBR8yv5/tPwAAAB5JREFUGNNjYCAHcK2CggXEc1hDoSCAeM5gtod0AADW6V+h4CpCKgAA
              ACV0RVh0ZGF0ZTpjcmVhdGUAMjAyMC0wMi0yN1QxMjozMTo1MC0wNzowMNnwhHMAAAAldEVYdGRh
              dGU6bW9kaWZ5ADIwMjAtMDItMjdUMTI6MzE6NTAtMDc6MDCorTzPAAAAAElFTkSuQmCC" />
            </svg>
          </div>
          <div class="p-2 align-self-center">
            <div class="d-flex flex-column">
              <div class="p-2">
                <span><a>` +
                song_info['title'] +
                `</a> Duration: ` +
                song_info['formatted_duration'] +
                `</span>
              </div>
            </div>
          </div>
          <div class="ml-auto p-2 align-self-center">
            <div class="dropdown dropleft">
              <a class="" href="#" role="button" id="dropdownMenuLink" data-toggle="dropdown">
                <svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" width="40px" height="40px" viewBox="0 0 40 40" enable-background="new 0 0 40 40" xml:space="preserve">  <image id="image0" width="40" height="40" x="0" y="0"
                  href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACgAAAAoCAMAAAC7IEhfAAAABGdBTUEAALGPC/xhBQAAACBjSFJN
              AAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAAV1BMVEUAAAAAAAAtDwwrDgsu
              DwzAPzGVMSctDgssDwyOLyXDQTMuEAsAAADCQDOOLyUsDguNLyWUMSYuDguPMCUoDgyOLyWQMCWP
              LyUAAADCQTMuEAznTDz///8dVoCNAAAAG3RSTlMAA65wrPnrcWnq+7IE++tv6etw623p6+oC+7Ho
              kTMcAAAAAWJLR0QcnARBBwAAAAd0SU1FB+QCGwUtHmA31a0AAADWSURBVDjLxdTdFoIgDADgiWVa
              KZL2y/u/ZwZBDLbVVe7KA587nrkNYO2oVE1f1KpCbrNtdpRru/3hiJy1lGw7axPpHCVfLpWqty6G
              7Dv14M97FV4c/UGW0+dbwpxAkoQjJekIybhCsi6T0TWFQ1J0S9mm9/UQHiZNN0DMKeYrJe+wlBzA
              fA7uIjqYr7/BWBdL9yflJIkdL2PBJ7ngyX9jOrlwbM8XTpBFv3ybo+a/c/RZAFnZQmHjArj5lcLN
              0f0Rl4+ThpmjxDlpyLZqR+SERarxIl0lnra6MGBtol6jAAAAJXRFWHRkYXRlOmNyZWF0ZQAyMDIw
              LTAyLTI3VDEyOjQ1OjMwLTA3OjAwP084DQAAACV0RVh0ZGF0ZTptb2RpZnkAMjAyMC0wMi0yN1Qx
              Mjo0NTozMC0wNzowME4SgLEAAAAASUVORK5CYII=" />
              </svg>
              </a>
              <div class="dropdown-menu" aria-labelledby="dropdownMenuLink">
                <a onclick="ban_control.call(this,event)" class="dropdown-item" href="#">Unban</a>
              </div>
            </div>
          </div>
          <div class="p-2 align-self-center">` +
                (song_info['favourite']
                    ? `
              <svg onclick="favourite_control.call(this,event)" version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" width="44px" height="36px" viewBox="0 0 44 36" enable-background="new 0 0 44 36" xml:space="preserve">  <image id="image0" width="44" height="36" x="0" y="0"
                  href="data:image/png;base64,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" />
              </svg>
          `
                    : `
              <svg onclick="favourite_control.call(this,event)" version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" width="44px" height="36px" viewBox="0 0 44 36" enable-background="new 0 0 44 36" xml:space="preserve">  <image id="image0" width="44" height="36" x="0" y="0"
                  href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACwAAAAkCAQAAABY3hDnAAAABGdBTUEAALGPC/xhBQAAACBjSFJN
              AAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAAAmJLR0QA/4ePzL8AAAAHdElN
              RQfkAhsFOBnJ5qYaAAACPElEQVRIx62WPWhTURiGn9x0soJOlkAnJ/EHpTRF6uKsm5MopYtLEUEI
              FBzaguAgIoYGoaVUInYRukjioA6iDbEUdXCq0hBpJW0URL2nTUvvva9DrW3T/Nwk95lfnvNyz3fO
              PSH2EuUqPXTQQZhf5PlEkln200s/pzjKIVyKFJljivdUoYs0TlxZ5WRU0rKyGhMOL+guW/wlzriy
              WlFJRjllFRcOac5U0g5iJuSoHEeTwmbof24E86hiblzYxMq1Cdy8qlEQHgkAHuKtVM0tCJfRvW1d
              R7VwhMcQw3hezdymcHdad2HyqkdB2NjLdXMLwub0lvj5RN24JNmyfeXGRApCRHnnhMMEh0ubS49F
              32igWgjzIEyfRXd3664yohC1iEQCF0cgEsKY9vaAxascXLXwvMAbu+BaFIuBi4tQtFhcDFy8BEsW
              mUzg4gxkQnQyH+z2rdG+xgmLb6QmA+2bhBRfAY5h+7sF/GCE4eT2IvevBya+IeI77S3mEoFoJ8VH
              2nZ/mOMU3rSsnRXf2Xf1XKa00JJ2WWzQX2k7Y2z+aFprhMtwtUm5XeuXWos/wuNerSEcpPShYe1n
              4XC33nxf43eqIW1WGG76OToXKDz2rX0qftLn91SeZf6WL+0dkeN8Iwf+MNMDqj0j6xoQr+lsRLs9
              IyZdVftKrP97djXBRb7EKjwAPY2IHJea1QIcIIkzs0c7KzyecaQV7RZXyMVkJEkbGhH5yge3ud4J
              zBNNiQ2mg+i6m17eMsM5v/G/N+7KqQlAhuoAAAAldEVYdGRhdGU6Y3JlYXRlADIwMjAtMDItMjdU
              MTI6NTY6MjUtMDc6MDCLZHP3AAAAJXRFWHRkYXRlOm1vZGlmeQAyMDIwLTAyLTI3VDEyOjU2OjI1
              LTA3OjAw+jnLSwAAAABJRU5ErkJggg==" />
              </svg>`) +
                `
              </div>
        </div>
      </td>
    </tr>`
        );
    });
}

function set_module_state(data) {
    paused = data['module_state']['paused'];
    video_showing = data['module_state']['video_showing'];
    enabled = data['module_state']['enabled'];
    requests_open = data['module_state']['requests_open'];
    use_backup_playlist = data['module_state']['use_backup_playlist'];

    $('#video_showing_state').text(video_showing ? 'Hide Video' : 'Show Video');
    $('#requests_open_state').text(
        requests_open ? 'Disable Requests' : 'Enable Requests'
    );
    $('#backup_playlist_usage_state').text(
        use_backup_playlist
            ? 'Disable Backup Playlist'
            : 'Enable Backup Playlist'
    );
    $('#control_state').text(paused ? 'Resume' : 'Pause');
    if (player.getDuration() > 0) {
        if (paused) {
            player.pauseVideo();
        } else {
            player.playVideo();
        }
    }
}

function initialize_player(data) {
    // volume
    set_volume(data);
    // module_state
    set_module_state(data);
    // current_song
    current_song(data);
    // playlist
    set_playlist(data);
    // backup_playlist
    set_backup_playlist(data);
    // history_list
    set_history_list(data);
    // favourite_list
    set_favourite_list(data);
    // banned_list
    set_banned_list(data);
}

$(document).ready(function() {
    var tag = document.createElement('script');

    tag.src = 'https://www.youtube.com/iframe_api';
    var firstScriptTag = document.getElementsByTagName('script')[0];
    firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

    $('#songname').hide();
    $('#url').hide();
});

var player;
function onYouTubeIframeAPIReady() {
    player = new YT.Player('video_player', {
        playerVars: { autoplay: 0, controls: 0, mute: 1 },
        videoId: '',
        events: {
            onReady: onPlayerReady,
            onStateChange: onPlayerStateChange,
        },
    });
    connect_to_ws();
}

function onPlayerReady(event) {
    player.playVideo();
}

var done = false;

function timer() {
    var playerTotalTime = player.getDuration();
    if (playerTotalTime == 0) {
        playerTotalTime++;
    }
    var playerCurrentTime = player.getCurrentTime();
    var playerTimeDifference = (playerCurrentTime / playerTotalTime) * 100;
    var minutes = Math.floor(playerCurrentTime / 60);
    var seconds = Math.floor(playerCurrentTime - minutes * 60);
    $('#videotime div').css('width', playerTimeDifference + '%');
    $('#videocurrenttime').text(minutes + ':' + ('0' + seconds).slice(-2));
}

function pause() {
    if (paused) {
        player.pauseVideo();
    }
}

function onPlayerStateChange(event) {
    if (paused) {
        setTimeout(pause, 1000);
    }
    timer();
    if (event.data == YT.PlayerState.PLAYING) {
        mytimer = setInterval(timer, 1000);
    } else {
        try {
            clearTimeout(mytimer);
        } catch {}
    }
}

$('#control_state').on('click', function(e) {
    if (!paused) {
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
});

$('#control_previous').on('click', function(e) {
    socket.send(
        JSON.stringify({
            event: 'PREVIOUS',
        })
    );
});

$('#control_next').on('click', function(e) {
    socket.send(
        JSON.stringify({
            event: 'NEXT',
        })
    );
});

$('#videotime').on('click', function(e) {
    socket.send(
        JSON.stringify({
            event: 'SEEK',
            data: {
                seek_time:
                    player.getDuration() *
                    ((e.pageX - $(this).offset().left) /
                        $('#videotime').width()),
            },
        })
    );
});

$('#volume').on('click', function(e) {
    socket.send(
        JSON.stringify({
            event: 'VOLUME',
            data: {
                volume: Math.round(
                    ((e.pageX - $(this).offset().left) / $('#volume').width()) *
                        100
                ),
            },
        })
    );
});

$('#requests_open_state').on('click', function(e) {
    socket.send(
        JSON.stringify({
            event: requests_open ? 'CLOSESR' : 'OPENSR',
        })
    );
});

$('#video_showing_state').on('click', function(e) {
    socket.send(
        JSON.stringify({
            event: video_showing ? 'HIDEVIDEO' : 'SHOWVIDEO',
        })
    );
});

function favourite_control(event) {
    console.log($(this));
    var tr = $(this).closest('tr');
    socket.send(
        JSON.stringify({
            event: tr.data('favourite') ? 'UNFAVOURITE' : 'FAVOURITE',
            data: tr.data('id')
                ? { database_id: tr.data('id') }
                : tr.data('infoid')
                ? { songinfo_database_id: tr.data('infoid') }
                : { hist_database_id: tr.data('histid') },
        })
    );
}

function ban_control(event) {
    var tr = $(this).closest('tr');
    socket.send(
        JSON.stringify({
            event: tr.data('banned') ? 'UNBAN' : 'BAN',
            data: tr.data('id')
                ? { database_id: tr.data('id') }
                : tr.data('infoid')
                ? { songinfo_database_id: tr.data('infoid') }
                : { hist_database_id: tr.data('histid') },
        })
    );
}

function delete_control(event) {
    var tr = $(this).closest('tr');
    socket.send(
        JSON.stringify({
            event: 'DELETE',
            data: { database_id: tr.data('id') },
        })
    );
}

var currentqueuebody = $('#currentqueuebody');
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
        console.log(sourceIndex + ' to ' + ui.item.index());
        socket.send(
            JSON.stringify({
                event: 'MOVE',
                data: {
                    database_id: ui.item.data('id'),
                    to_id: ui.item.index() + 1,
                },
            })
        );
        setTimeout(function() {
            currentqueuebody.sortable('cancel');
        }, 0);
    },
});
