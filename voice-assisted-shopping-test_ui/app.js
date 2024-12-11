// Reference: https://developer.mozilla.org/en-US/docs/Web/API/MediaStream_Recording_API/Using_the_MediaStream_Recording_API

// Set up basic variables for app
const record = document.querySelector('.record');
const stop = document.querySelector('.stop');
const soundClips = document.querySelector('.sound-clips');
const canvas = document.querySelector('.visualizer');
const mainSection = document.querySelector('.main-controls');

// Disable stop button while not recording
stop.disabled = true;

// Visualizer setup - create web audio API context and canvas
let audioCtx;
const canvasCtx = canvas.getContext("2d");

// Main block for doing the audio recording
if (navigator.mediaDevices.getUserMedia) {
    console.log('getUserMedia supported.');

    const constraints = { audio: true };
    let chunks = [];

    // Function to handle recording start
    function keyDown(mediaRecorder) {
        mediaRecorder.start();
        console.log(mediaRecorder.state);
        console.log("Recorder started");
        record.style.background = "red";

        stop.disabled = false;
        record.disabled = true;
    }

    // Function to handle recording stop
    function keyUp(mediaRecorder) {
        mediaRecorder.stop();
        console.log(mediaRecorder.state);
        console.log("Recorder stopped");
        record.style.background = "";
        record.style.color = "";

        stop.disabled = true;
        record.disabled = false;
    }

    function onSuccessWithSpace(stream) {
        const mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm" });

        visualize(stream);

        // Event listener for recording control using spacebar
        window.addEventListener('keydown', function (e) {
            if (e.key === ' ' || e.key === 'Spacebar') {
                e.preventDefault();
                keyDown(mediaRecorder);
            }
        });

        window.addEventListener('keyup', function (e) {
            if (e.key === ' ' || e.key === 'Spacebar') {
                keyUp(mediaRecorder);
            }
        });

        // Event listener for recording control using mouse buttons
        window.addEventListener('mousedown', function (e) {
            if (e.button === 0) {
                keyDown(mediaRecorder);
            }
        });

        window.addEventListener('mouseup', function (e) {
            if (e.button === 0) {
                keyUp(mediaRecorder);
            }
        });

        // Handle data available event to process recorded chunks
        mediaRecorder.ondataavailable = function (e) {
            chunks.push(e.data);
        }

        // Handle stop event to process and send audio data
        mediaRecorder.onstop = function (e) {
            console.log("Data available after MediaRecorder.stop() called.");
            const blob = new Blob(chunks, { type: "audio/webm" });

            // Sending audio data to backend
            var fd = new FormData();
            fd.append('session', 'abcdefg123456');
            fd.append('fname', 'input.webm');
            fd.append('data', blob);
            console.log("FormData: ", fd);

            axios({
                url: 'http://localhost:8000/audio-chatbot',
                method: 'POST',
                data: fd,
                responseType: 'blob'
            })
                .then(function (response) {
                    var audioUrl = URL.createObjectURL(response.data);
                    var audio = new Audio(audioUrl);
                    audio.play();
                })
                .catch(function (error) {
                    console.log(error);
                });

            chunks = [];
        }
    }

    function onError(err) {
        console.log('The following error occurred: ' + err);
    }

    navigator.mediaDevices.getUserMedia(constraints).then(onSuccessWithSpace, onError);

} else {
    console.log('getUserMedia not supported on your browser!');
}

// Visualizer function to draw the audio stream
function visualize(stream) {
    if (!audioCtx) {
        audioCtx = new AudioContext();
    }

    const source = audioCtx.createMediaStreamSource(stream);
    const analyser = audioCtx.createAnalyser();
    analyser.fftSize = 2048;
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    source.connect(analyser);

    draw();

    function draw() {
        const WIDTH = canvas.width;
        const HEIGHT = canvas.height;

        requestAnimationFrame(draw);

        analyser.getByteTimeDomainData(dataArray);

        canvasCtx.fillStyle = 'rgb(200, 200, 200)';
        canvasCtx.fillRect(0, 0, WIDTH, HEIGHT);

        canvasCtx.lineWidth = 2;
        canvasCtx.strokeStyle = 'rgb(0, 0, 0)';

        canvasCtx.beginPath();

        let sliceWidth = WIDTH * 1.0 / bufferLength;
        let x = 0;

        for (let i = 0; i < bufferLength; i++) {
            let v = dataArray[i] / 128.0;
            let y = v * HEIGHT / 2;

            if (i === 0) {
                canvasCtx.moveTo(x, y);
            } else {
                canvasCtx.lineTo(x, y);
            }

            x += sliceWidth;
        }

        canvasCtx.lineTo(canvas.width, canvas.height / 2);
        canvasCtx.stroke();
    }
}

// Adjust canvas size when window is resized
window.onresize = function () {
    canvas.width = mainSection.offsetWidth;
}

window.onresize();
