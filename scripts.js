


let hostAddr;
let hostPort;
let myUserName;
let myID;        // 7-digit unique identifier assigned by host
let myIndex;
let sock;         //WebSocket connection object
let players=[];
let points = [];
let article_options=[];
let state;
let judge;
let truther;
let timer;
let gametimer;
let turn;
let title;
let fact;
let article;
let winner;
let twowinners = [];
let tie = false;
let winner1;
let winner2;
let is_timer_running = false;


function startGame(){

	document.getElementById("invalids").innerHTML = null;
	hostAddr = document.startpage.hostaddr.value;
	hostPort = document.startpage.hostport.value;
	myUserName = document.startpage.myusername.value;
	console.log(hostAddr);
	console.log(hostPort);
	console.log(myUserName);
	if (validateAddr(hostAddr) || validatePort(hostPort) || validateUserName(myUserName)) { 
		return false;
	};
	url = `ws://${hostAddr.toString()}:${hostPort.toString()}`;
	connectToHost(url);
	return false;
};

function connectToHost(url){
	sock = new WebSocket(url);
	sock.onopen = function(event) {
		sock.send(`username=${myUserName}`);
		console.log(myUserName);
	};
	sock.onclose = function(event) {
		if (state != 'endgame'){
			while (sock.readyState != 0 && sock.readyState != 1){
				connectToHost(url);
			};
		};
	};
	sock.onmessage = function(event) {
		inmsg = event.data;
		parseData(inmsg);
	};	
};


function parseData(message){
	message = message.replace(/\'/g, '').replace(/\[/g , '').replace(/\]/g, '');
	console.log(message);
	if (message.indexOf("&this_game_article=") != -1){
		splitMessage = message.split('&this_game_article=');
		message = splitMessage[0];
		article = splitMessage[1];
		console.log(article);
	};
	if (message.indexOf('&this_game_title=') != -1){
		splitMessage = message.split('&this_game_title=');
		message = splitMessage[0];
		title = splitMessage[1];
	};
	if (message.indexOf('&this_game_options=') != -1){
		splitMessage = message.split('&this_game_options=');
		message = splitMessage[0];
		article_options = splitMessage[1].split(',');
	};
	if (message.indexOf('&') != -1){
		splitMessage = message.split('&');
		for (let msg of splitMessage) {
			msgPair = msg.split('=')
			switch (msgPair[0]){
				case 'playerid':
					myID = msgPair[1];
					break;
				case 'index':
					myIndex = Number(msgPair[1]);
					break;
				case 'state':
					state = msgPair[1];
					break;
				case 'players':
					if (msgPair[1].indexOf(',') != -1){
						players = msgPair[1].split(',');
					}
					else {
						players = [msgPair[1]];
					};
					doPlayerHTML();
					break;
				case 'judge':
					if (msgPair[1] != '-1'){
						judge = Number(msgPair[1]);
					};
					break;
				case 'truther':
					truther = Number(msgPair[1]);
					break;
				case 'timer':
					timer = Number(msgPair[1]);
					break;
				case 'turn':
					turn = Number(msgPair[1]);
					break;
				case 'points':
					points = msgPair[1].split(',');
					break;
				case 'winner':
					winner = Number(msgPair[1]);
					break;
				case 'error':
					handleError(msgPair[1]);
					break;
				case 'gamewinner':
					if (msgPair[1].indexOf('+') != -1){
						twowinners = msgPair[1].split('+');
						tie = true;
						winner1 = Number(twowinners[0]);
						winner2 = Number(twowinners[1]);
					}
					else {
					winner1 = Number(msgPair[1]);
				};
			};
		};
		setGameState();
	};
};

function handleError(error) {
	if (error == 'lobbyfull'){
		if (document.getElementById('invalids') != null){
			document.getElementById('invalids').innerHTML = '<u>Error:</u> This game lobby is full.';
		}
		else {
		document.getElementById('centeringdiv').innerHTML = '<div class="title">Error</div><br><div class="subtitle">This lobby is... somehow full? <br> Maybe refresh and try again?</div>'
		};
	};
};

function setGameState(){
	let waitstart = `<div id=\"waitstart\"><b><u>Success!</u></b>
			<br><br>
	  	Hang tight! When the host starts the game, this window will update automatically.
			</div>`;
	doPlayerHTML();
	switch (state) {
		case 'waitstart':
			document.getElementById('centeringdiv').innerHTML = waitstart;
			break;
		case 'choosingfact':
			document.getElementById('centeringdiv').innerHTML = articleOptions();
			console.log(article_options);
			break;
		case 'memorize':
			document.getElementById('centeringdiv').innerHTML = memorizeArticle();
			// document.getElementById('gamearea').style.pointerEvents = 'none';
			break;
		case 'explain':
			document.getElementById('centeringdiv').innerHTML = explain();
			break;
		case 'choosingwinner':
			// document.getElementById('gamearea').style.pointerEvents = 'auto';
			document.getElementById('centeringdiv').innerHTML = chooseWinner();
			break;
		case 'endround':
			document.getElementById('centeringdiv').innerHTML = endRound();
			break;
		case 'endgame':
			document.getElementById('centeringdiv').innerHTML = endGame();
			break;
	};
	if (timer > 0 && is_timer_running == false){
		gametimer = setInterval(startGameTimer, 1000);
		is_timer_running = true;
	};
};

function doPlayerHTML(){
	let playerhtml = '';
	let turnarrow;
	if (Array.isArray(players)){
		for (let this_player of players){
			if ((turn == players.indexOf(this_player)) || (state == 'choosingwinner' && judge == players.indexOf(this_player))) {
				turnarrow = '<img class="turnarrow" src="turnarrow.png" alt=""/>';
			}
			else {
				turnarrow = '';
			};

			if (judge == players.indexOf(this_player)){
			  playerhtml = `${playerhtml}<div class="player" style="background-color: #BA160C;">${turnarrow}${this_player}<div class="points">${points[players.indexOf(this_player)]}</div></div>`;
			}
			else {
				playerhtml = `${playerhtml}<div class="player">${turnarrow}${this_player}<div class="points">${points[players.indexOf(this_player)]}</div></div>`;
			};
			
		};
	}
	else if (typeof players == "string"){
		playerhtml = `<div class="player">${players}</div>`;		
	};

	document.getElementById('players').innerHTML = playerhtml;
};

function articleOptions(){
	if (truther == myIndex){
		let optionshtml = `<div class="title">You are the truther!</div>
				<div class="subtitle">Please choose an article:</div>
        <br>`;
		if (Array.isArray(article_options)){
			let opnum = 0;
			for (let option of article_options){
				optionshtml = `${optionshtml}<div class="option" onclick="chooseArticleOption(${opnum})">${option}</div>`;
				opnum = opnum + 1;
			};
		};
		return optionshtml;
	}
	else if (judge == myIndex){
		return `<div class="title">You are the judge!</div>
        <br>
        <br>
        <div class="descrip">
          In a moment, you'll have to decide who is telling the truth!
          <br><i>(Please wait while the truther chooses an article)</i>
        </div>
      </div>
    </div>`
	}
	else {
		return `<div class="title">You are a liar!</div>
        <br>
        <br>
        <div class="descrip">
          Please wait while the truther picks an article.
        </div>
      </div>
    </div>`
	}
};

function chooseArticleOption(opnum){
	document.getElementById('centeringdiv').innerhtml = '';
	sock.send(`proceed=true&articlechoice=${opnum}`);
};


function memorizeArticle(){
	if (truther == myIndex){
		return article 
	}
	else if (judge == myIndex){
		return `
        <div class="title">${players.length - 2} lies and a truth</div>
        <br>
        <br>
        <div class="descrip">
          One of these people will tell the truth, but the other ${players.length - 2} are liars!
          <br>
          Once the timer runs out, it'll be up to you to listen and decide who's telling the truth.
        </div>`;
	} 
	else {
		return `<div class="title">Make something up about:</div>
        <div class="subtitle">${title}</div>
        <br>
        <br>
        <div class="descrip">
          Think of a fake explanation for what <b>"${title}"</b>could be!
          <br>
          <i>(Remember: If you know what it is, you <u>must</u> make up a <u>lie</u>!)</i>
        </div>`;
	};
};

function explain(){
	if (turn == myIndex && truther == myIndex){
		return `<div class="title">Tell the truth!</div>
        <br>
        <br>
        <div class="descrip">
          Time to tell us everything you learned about ${title}!
        </div>`;
	}
	else if (turn != myIndex && judge == myIndex){
		return `<div class="title">Who's telling the truth?</div>
        <br>
        <br>
        <div class="descrip">
          Does ${players[turn]} sound like they know anything about <b>"${title}"</b>?
        </div>`;
	}
	else if (turn == myIndex && truther != myIndex){
		return `<div class="title">Make something up!</div>
        <br>
        <br>
        <div class="descrip">
          Pretend you know all about <b>"${title}"</b>!
        </div>`;
	}
	else {
		return `<div class="title">Not your turn!</div>
        <br>
        <br>
        <div class="descrip">
          Please wait while ${players[turn]} talks about <b>"${title}"</b>.
        </div>`;
	};
};

function chooseWinner(){
	if (judge == myIndex){
		let optionshtml = `<div class="title">Who do you think is telling the truth?</div>
	        <br>
	        <br>`;
		let opnum = 0;
		for (let option of players){
			if (opnum != judge){
				optionshtml = `${optionshtml}<div class="option" onclick="chooseWinnerOption(${opnum})">${option}</div><br>`;
			};
			opnum = opnum + 1;
		};
		return optionshtml;
	}
	else {
		return `<div class="title">You are being judged!</div>
	        <br>
	        <br>
	        <div class="descrip">
	          Answer questions while the judge (${players[judge]}) decides who they think is telling the truth about <b>${title}</b>.
	        </div>`;
	};
};

function chooseWinnerOption(opnum){
	document.getElementById('centeringdiv').innerHTML = '';
	winner = opnum;
	sock.send(`proceed=true&winnerchoice=${opnum}`);
};

function endRound(){
	if (truther == winner){
		return `<div class="title">CORRECT!</div>
        <div class="subtitle">${players[truther]} was telling the truth!</div>
        <br>
        <br>
        <div class="descrip">
          ${players[truther]} got 1 point for being chosen
          <br>
          <br>
          <b>AND</b>
          <br>
          <br>
          ${players[judge]} got 1 point for choosing correctly!
          </div>`;
	}
	else if (truther != winner){
		return `<div class="title">WRONG!</div>
      <div class="subtitle">${players[winner]} was lying!
      <br>${players[truther]} was telling the truth!</div>
      <br>
      <br>
      <div class="descrip">
        ${players[winner]} got 1 point for being chosen.
      </div>`;
	};
};

function endGame(){
	if (tie == true){
		return `<div class="title">TIE GAME!</div>
      <div class="subtitle">Both ${players[winner1]} and ${players[winner2]} reached the point total at the same time!</div>
      <br>
      <br>
      <div class="descrip">
      Thank you for playing! If you'd like to play again, have the host start another game and refresh this page.
      <br>
      <br>
      <i>If you enjoyed this game, feel free to share it with your friends.
      If enough people show interest, I might consider setting up a server, so you won't need anyone to download a host.
      </i>
      </div>`;
	}
	else if (tie != true){
		return `<div class="title">${players[winner1]} WINS!</div>
      <br>
      <br>
      <div class="descrip">
      Thank you for playing! If you'd like to play again, have the host start another game and refresh this page.
      <br>
      <br>
      <i>If you enjoyed this game, feel free to share it with your friends.
      If enough people show interest, I might consider setting up a server, so you won't need anyone to download a host.
      </i>
      </div>`;
	};
};

function startGameTimer(){
	document.getElementById("timer").innerHTML = timer;
  if (timer <= 0){
  	document.getElementById("timer").innerHTML = 'X';
    clearInterval(gametimer);
    is_timer_running = false;
   };
   timer-=1;
};


function validateAddr(addr){
	const ipformat = /^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
	if (addr.match(ipformat)) {
		return false;
	} 
	else {
		document.getElementById("invalids").innerHTML = "You have entered an <u>invalid IP Address</u>";
		return true;
	};
};

function validatePort(prt) {
	if (prt < 1 || prt > 65535) {
		document.getElementById("invalids").innerHTML = "You have entered an <u>invalid Port number</u>";
		return true;
	}
	else {
		return false;
	};
};

function validateUserName(name){
	if(name.match(/^[a-zA-Z0-9 ]+$/) && name.length < 17){
		return false;
	}
	else {
		document.getElementById("invalids").innerHTML = "<u>Invalid username.</u><br>Username may only contain letters, numbers, and spaces.<br> Usernames can be no longer than 16 characters.";
		return true;
	}
}