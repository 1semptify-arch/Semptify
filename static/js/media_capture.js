/**
 * Mobile media capture for tenant evidence.
 *
 * Supports camera photos and audio recordings via getUserMedia, with a
 * factual recording-consent note and immediate upload to /api/media/capture.
 * Captured vault IDs are added as hidden inputs to the capture form so they
 * are attached to the timeline event.
 */

(function () {
    "use strict";

    const RECODING_CONSENT_TEXT =
        "Recording laws vary by state. Minnesota is one-party consent, but " +
        "check your own state's law before recording conversations. This is a " +
        "factual note, not legal advice.";

    const MEDIA_SUPPORTED = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);

    /**
     * Build the capture UI into `container` and wire it to `form`.
     */
    function initMediaCapture(container, form) {
        if (!MEDIA_SUPPORTED) {
            container.innerHTML = '<p class="media-capture__notice">Your browser does not support camera or microphone capture.</p>';
            return;
        }

        container.innerHTML = '';
        const wrapper = document.createElement('div');
        wrapper.className = 'media-capture';

        wrapper.innerHTML = `
            <div class="media-capture__controls">
                <button type="button" class="btn btn--secondary" data-action="photo">Take photo</button>
                <button type="button" class="btn btn--secondary" data-action="audio">Record audio</button>
            </div>
            <div class="media-capture__consent">${RECODING_CONSENT_TEXT}</div>
            <div class="media-capture__stage" hidden></div>
            <div class="media-capture__gallery"></div>
        `;
        container.appendChild(wrapper);

        const stage = wrapper.querySelector('.media-capture__stage');

        wrapper.querySelectorAll('[data-action]').forEach((btn) => {
            btn.addEventListener('click', () => {
                const action = btn.dataset.action;
                if (action === 'photo') {
                    openPhotoCapture(stage, form);
                } else if (action === 'audio') {
                    openAudioCapture(stage, form);
                }
            });
        });
    }

    /**
     * Open the photo capture workflow.
     */
    async function openPhotoCapture(stage, form) {
        stage.hidden = false;
        stage.innerHTML = `
            <div class="media-capture__preview-wrap">
                <video class="media-capture__preview" autoplay playsinline muted></video>
                <canvas class="media-capture__canvas" hidden></canvas>
                <img class="media-capture__photo-result" hidden alt="Captured photo">
            </div>
            <div class="media-capture__actions">
                <button type="button" class="btn btn--primary" data-action="snap">Capture</button>
                <button type="button" class="btn btn--secondary" data-action="retake" hidden>Retake</button>
                <button type="button" class="btn btn--primary" data-action="use" hidden>Use this photo</button>
                <button type="button" class="btn btn--secondary" data-action="cancel">Cancel</button>
            </div>
        `;

        const video = stage.querySelector('video');
        const canvas = stage.querySelector('canvas');
        const resultImg = stage.querySelector('img');
        const snapBtn = stage.querySelector('[data-action="snap"]');
        const retakeBtn = stage.querySelector('[data-action="retake"]');
        const useBtn = stage.querySelector('[data-action="use"]');
        const cancelBtn = stage.querySelector('[data-action="cancel"]');

        let stream = null;
        let currentBlob = null;

        try {
            stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" }, audio: false });
            video.srcObject = stream;
            await video.play();
        } catch (err) {
            stage.innerHTML = `<p class="media-capture__notice">Could not access camera: ${err.message}</p>`;
            return;
        }

        function stopStream() {
            if (stream) {
                stream.getTracks().forEach((track) => track.stop());
                stream = null;
            }
        }

        snapBtn.addEventListener('click', () => {
            canvas.width = video.videoWidth || 640;
            canvas.height = video.videoHeight || 480;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

            stopStream();
            video.hidden = true;
            snapBtn.hidden = true;

            canvas.toBlob((blob) => {
                currentBlob = blob;
                resultImg.src = URL.createObjectURL(blob);
                resultImg.hidden = false;
                canvas.hidden = true;
                retakeBtn.hidden = false;
                useBtn.hidden = false;
            }, 'image/jpeg', 0.92);
        });

        retakeBtn.addEventListener('click', () => {
            openPhotoCapture(stage, form);
        });

        useBtn.addEventListener('click', async () => {
            useBtn.disabled = true;
            useBtn.textContent = 'Saving...';
            try {
                const vaultId = await uploadBlob(currentBlob, 'photo', 'captured_photo.jpg');
                addAttachment(form, vaultId, 'photo');
                closeStage(stage);
            } catch (err) {
                showFlash('Could not save photo. Please try again.', 'error');
                useBtn.disabled = false;
                useBtn.textContent = 'Use this photo';
            }
        });

        cancelBtn.addEventListener('click', () => {
            stopStream();
            closeStage(stage);
        });
    }

    /**
     * Open the audio recording workflow.
     */
    async function openAudioCapture(stage, form) {
        stage.hidden = false;
        stage.innerHTML = `
            <div class="media-capture__preview-wrap">
                <div class="media-capture__audio-status">Ready to record</div>
                <audio class="media-capture__audio-result" controls hidden></audio>
            </div>
            <div class="media-capture__actions">
                <button type="button" class="btn btn--primary" data-action="record">Start recording</button>
                <button type="button" class="btn btn--secondary" data-action="stop" hidden>Stop recording</button>
                <button type="button" class="btn btn--primary" data-action="use" hidden>Use this recording</button>
                <button type="button" class="btn btn--secondary" data-action="retake" hidden>Retake</button>
                <button type="button" class="btn btn--secondary" data-action="cancel">Cancel</button>
            </div>
        `;

        const statusEl = stage.querySelector('.media-capture__audio-status');
        const audioEl = stage.querySelector('audio');
        const recordBtn = stage.querySelector('[data-action="record"]');
        const stopBtn = stage.querySelector('[data-action="stop"]');
        const useBtn = stage.querySelector('[data-action="use"]');
        const retakeBtn = stage.querySelector('[data-action="retake"]');
        const cancelBtn = stage.querySelector('[data-action="cancel"]');

        let stream = null;
        let recorder = null;
        let chunks = [];
        let currentBlob = null;

        try {
            stream = await navigator.mediaDevices.getUserMedia({ video: false, audio: true });
        } catch (err) {
            stage.innerHTML = `<p class="media-capture__notice">Could not access microphone: ${err.message}</p>`;
            return;
        }

        function stopStream() {
            if (stream) {
                stream.getTracks().forEach((track) => track.stop());
                stream = null;
            }
        }

        recordBtn.addEventListener('click', () => {
            chunks = [];
            const mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4';
            recorder = new MediaRecorder(stream, { mimeType });

            recorder.ondataavailable = (e) => {
                if (e.data.size > 0) chunks.push(e.data);
            };

            recorder.onstop = () => {
                currentBlob = new Blob(chunks, { type: mimeType });
                audioEl.src = URL.createObjectURL(currentBlob);
                audioEl.hidden = false;
                statusEl.textContent = 'Recording complete';
                stopBtn.hidden = true;
                recordBtn.hidden = true;
                useBtn.hidden = false;
                retakeBtn.hidden = false;
            };

            recorder.start();
            statusEl.textContent = 'Recording...';
            recordBtn.hidden = true;
            stopBtn.hidden = false;
        });

        stopBtn.addEventListener('click', () => {
            if (recorder && recorder.state !== 'inactive') {
                recorder.stop();
            }
            stopStream();
        });

        retakeBtn.addEventListener('click', () => {
            openAudioCapture(stage, form);
        });

        useBtn.addEventListener('click', async () => {
            useBtn.disabled = true;
            useBtn.textContent = 'Saving...';
            try {
                const ext = currentBlob.type.includes('mp4') ? 'mp4' : 'webm';
                const vaultId = await uploadBlob(currentBlob, 'audio', `recording_${Date.now()}.${ext}`);
                addAttachment(form, vaultId, 'audio');
                closeStage(stage);
            } catch (err) {
                showFlash('Could not save recording. Please try again.', 'error');
                useBtn.disabled = false;
                useBtn.textContent = 'Use this recording';
            }
        });

        cancelBtn.addEventListener('click', () => {
            if (recorder && recorder.state !== 'inactive') {
                recorder.stop();
            }
            stopStream();
            closeStage(stage);
        });
    }

    /**
     * Upload a captured blob to the server and return the vault_id.
     */
    async function uploadBlob(blob, mediaType, filename) {
        const formData = new FormData();
        formData.append('file', blob, filename);
        formData.append('media_type', mediaType);

        const response = await window.fetchWithCSRF('/api/media/capture', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const text = await response.text();
            throw new Error(`Upload failed: ${response.status} ${text}`);
        }

        const result = await response.json();
        if (!result.success || !result.vault_id) {
            throw new Error('Upload did not return a vault_id');
        }
        return result.vault_id;
    }

    /**
     * Append a hidden input to the form with the captured vault_id.
     */
    function addAttachment(form, vaultId, mediaType) {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'attached_document_ids';
        input.value = vaultId;
        input.dataset.mediaType = mediaType;
        form.appendChild(input);

        const gallery = form.querySelector('.media-capture__gallery') ||
                        form.parentElement.querySelector('.media-capture__gallery');
        if (gallery) {
            const item = document.createElement('div');
            item.className = 'media-capture__gallery-item';
            item.dataset.vaultId = vaultId;
            item.innerHTML = `
                <span>${mediaType === 'photo' ? 'Photo' : 'Audio'} captured</span>
                <button type="button" class="media-capture__remove" aria-label="Remove">Remove</button>
            `;
            item.querySelector('button').addEventListener('click', () => {
                input.remove();
                item.remove();
            });
            gallery.appendChild(item);
        }
    }

    function closeStage(stage) {
        stage.hidden = true;
        stage.innerHTML = '';
    }

    window.initMediaCapture = function (selector, formSelector) {
        const container = document.querySelector(selector);
        const form = document.querySelector(formSelector);
        if (!container || !form) {
            console.warn('initMediaCapture: missing container or form', selector, formSelector);
            return;
        }
        initMediaCapture(container, form);
    };
})();
