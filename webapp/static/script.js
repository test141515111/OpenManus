// Main script for OpenManus Web UI
document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const taskForm = document.getElementById('taskForm');
    const queryInput = document.getElementById('queryInput');
    const submitBtn = document.getElementById('submitBtn');
    const taskStatus = document.getElementById('taskStatus');
    const currentTask = document.getElementById('currentTask');
    const screenshotsList = document.getElementById('screenshotsList');
    const videosList = document.getElementById('videosList');
    const resultsList = document.getElementById('resultsList');
    const noScreenshots = document.getElementById('noScreenshots');
    const noVideos = document.getElementById('noVideos');
    const noResults = document.getElementById('noResults');
    
    // Initialize Socket.IO if available
    let socket = null;
    try {
        socket = io();
        
        // Socket.IO event handlers
        socket.on('connect', function() {
            console.log('Connected to server via Socket.IO');
            // Request current status after connection
            socket.emit('request_task_status');
        });
        
        socket.on('disconnect', function() {
            console.log('Disconnected from server');
        });
        
        socket.on('task_update', function(data) {
            console.log('Task update received:', data);
            updateTaskStatus(data);
        });
        
        socket.on('new_screenshot', function(data) {
            console.log('New screenshot received');
            addScreenshot(data);
        });
        
        socket.on('new_video', function(data) {
            console.log('New video received');
            addVideo(data);
        });
        
        socket.on('task_status_update', function(data) {
            console.log('Status update received:', data);
            updateTaskStatus(data);
        });
    } catch (e) {
        console.log('Socket.IO not available, falling back to HTTP API');
        socket = null;
    }
    
    // Submit task form
    taskForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const query = queryInput.value.trim();
        if (!query) {
            alert('タスクや質問を入力してください');
            return;
        }
        
        // Disable form while task is running
        submitBtn.disabled = true;
        submitBtn.innerHTML = '送信中... <span class="loading"></span>';
        
        // Update UI immediately
        taskStatus.textContent = 'Running';
        currentTask.textContent = query;
        
        // Clear previous results
        screenshotsList.innerHTML = '';
        if (videosList) videosList.innerHTML = '';
        resultsList.innerHTML = '';
        
        if (noScreenshots) noScreenshots.style.display = 'block';
        if (noVideos) noVideos.style.display = 'block';
        if (noResults) noResults.style.display = 'block';
        
        // Submit task via Socket.IO if available, otherwise use HTTP API
        if (socket && socket.connected) {
            socket.emit('submit_task', { query: query });
        } else {
            // Submit task to API
            fetch('/api/task', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ task: query })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Task submitted successfully
                    console.log('Task submitted successfully');
                    // Start polling for updates
                    startPolling();
                } else {
                    alert('エラー: ' + data.message);
                    resetForm();
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('タスクの送信中にエラーが発生しました');
                resetForm();
            });
        }
    });
    
   // Function to update task status
    function updateTaskStatus(data) {
        const status = data.status;
        
        // Translate status to Japanese
        let statusText = '待機中';
        if (status === 'running') statusText = '実行中';
        else if (status === 'completed') statusText = '完了';
        else if (status === 'failed') statusText = '失敗';
        else if (status === 'idle') statusText = '待機中';
        
        taskStatus.textContent = statusText;
        
        if (data.task) {
            currentTask.textContent = data.task;
        }
        
        // Update screenshots if available
        if (data.screenshots && data.screenshots.length > 0) {
            screenshotsList.innerHTML = '';
            data.screenshots.forEach(screenshot => {
                addScreenshot(screenshot);
            });
        }
        
        // Update videos if available
        if (data.videos && data.videos.length > 0 && videosList) {
            videosList.innerHTML = '';
            data.videos.forEach(video => {
                addVideo(video);
            });
        }
        
        // Update results if available
        if (data.results) {
            if (noResults) noResults.style.display = 'none';
            resultsList.innerHTML = '<pre>' + JSON.stringify(data.results, null, 2) + '</pre>';
        }
        
        if (status === 'completed' || status === 'failed') {
            resetForm();
            
            if (data.error) {
                if (noResults) noResults.style.display = 'none';
                resultsList.innerHTML = '<div class="error">エラー: ' + data.error + '</div>';
            }
        }
    }
    
    // Function to add a screenshot
    function addScreenshot(data) {
        if (noScreenshots) noScreenshots.style.display = 'none';
        
        const screenshotItem = document.createElement('div');
        screenshotItem.className = 'screenshot-item';
        
        const timestamp = document.createElement('div');
        timestamp.className = 'timestamp';
        timestamp.textContent = data.timestamp;
        
        const img = document.createElement('img');
        img.src = `data:image/png;base64,${data.data}`;
        img.alt = 'ブラウザのスクリーンショット';
        img.className = 'screenshot-img';
        
        screenshotItem.appendChild(timestamp);
        screenshotItem.appendChild(img);
        
        // Add to the beginning of the list (newest first)
        screenshotsList.insertBefore(screenshotItem, screenshotsList.firstChild);
    }
    
    // Function to add a video
    function addVideo(data) {
        if (!videosList) return;
        
        if (noVideos) noVideos.style.display = 'none';
        
        const videoItem = document.createElement('div');
        videoItem.className = 'video-item';
        
        const timestamp = document.createElement('div');
        timestamp.className = 'timestamp';
        timestamp.textContent = data.timestamp;
        
        const video = document.createElement('video');
        video.controls = true;
        video.autoplay = false;
        video.className = 'video-player';
        
        const source = document.createElement('source');
        source.src = `data:video/webm;base64,${data.data}`;
        source.type = 'video/webm';
        
        video.appendChild(source);
        videoItem.appendChild(timestamp);
        videoItem.appendChild(video);
        
        // Add to the beginning of the list (newest first)
        videosList.insertBefore(videoItem, videosList.firstChild);
    }
    
    // Reset form after task completion
    function resetForm() {
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'タスクを送信';
    }
    
    // Poll for updates if Socket.IO is not available
    let pollingInterval = null;
    
    function startPolling() {
        if (pollingInterval) clearInterval(pollingInterval);
        
        pollingInterval = setInterval(function() {
            fetch('/api/task_status')
                .then(response => response.json())
                .then(data => {
                    updateTaskStatus(data);
                    
                    if (data.status === 'completed' || data.status === 'failed') {
                        clearInterval(pollingInterval);
                    }
                })
                .catch(error => {
                    console.error('Error polling for updates:', error);
                });
        }, 2000);
    }
    
    // Initial status check via HTTP API
    fetch('/api/task_status')
        .then(response => response.json())
        .then(data => {
            if (data.status !== 'idle') {
                updateTaskStatus(data);
                
                if (data.status === 'running') {
                    startPolling();
                }
            }
        })
        .catch(error => {
            console.error('Error fetching initial task status:', error);
        });
});
