// Socket.IO client for OpenManus Web UI
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Socket.IO connection
    const socket = io();
    
    // DOM elements
    const taskStatus = document.getElementById('taskStatus');
    const currentTask = document.getElementById('currentTask');
    const noScreenshots = document.getElementById('noScreenshots');
    const screenshotsList = document.getElementById('screenshotsList');
    const noVideos = document.getElementById('noVideos');
    const videosList = document.getElementById('videosList');
    const noResults = document.getElementById('noResults');
    const resultsList = document.getElementById('resultsList');
    const taskForm = document.getElementById('taskForm');
    const queryInput = document.getElementById('queryInput');
    const submitBtn = document.getElementById('submitBtn');
    
    // Connect event
    socket.on('connect', function() {
        console.log('Connected to server');
        
        // Request initial task status
        socket.emit('request_task_status');
        
        // Request initial screenshots
        socket.emit('request_screenshots');
        
        // Request initial videos
        socket.emit('request_videos');
    });
    
    // Disconnect event
    socket.on('disconnect', function() {
        console.log('Disconnected from server');
    });
    
    // Submit task form
    taskForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const query = queryInput.value.trim();
        if (!query) {
            alert('Please enter a task or question');
            return;
        }
        
        // Disable form while task is running
        submitBtn.disabled = true;
        submitBtn.innerHTML = 'Submitting...';
        
        // Submit task to server
        socket.emit('submit_task', { query: query });
    });
    
    // Task update event
    socket.on('task_update', function(data) {
        console.log('Task update:', data);
        
        // Update status
        taskStatus.textContent = capitalizeFirstLetter(data.status);
        taskStatus.className = 'status-' + data.status;
        
        // Update current task
        if (data.task) {
            currentTask.textContent = data.task;
        }
        
        // Update results
        if (data.results) {
            updateResults(data.results);
        }
        
        // If task is completed or failed, reset form
        if (data.status === 'completed' || data.status === 'failed') {
            submitBtn.disabled = false;
            submitBtn.innerHTML = 'Submit Task';
        }
    });
    
    // Task status update event
    socket.on('task_status_update', function(data) {
        console.log('Task status update:', data);
        
        // Update status
        taskStatus.textContent = capitalizeFirstLetter(data.status);
        taskStatus.className = 'status-' + data.status;
        
        // Update current task
        currentTask.textContent = data.task || 'None';
        
        // Update screenshots
        if (data.screenshots) {
            updateScreenshots(data.screenshots);
        }
        
        // Update videos
        if (data.videos) {
            updateVideos(data.videos);
        }
        
        // Update results
        if (data.results) {
            updateResults(data.results);
        }
    });
    
    // New screenshot event
    socket.on('new_screenshot', function(screenshot) {
        console.log('New screenshot:', screenshot);
        
        // Add screenshot to list
        addScreenshot(screenshot);
    });
    
    // Screenshots update event
    socket.on('screenshots_update', function(data) {
        console.log('Screenshots update:', data);
        
        // Update screenshots
        updateScreenshots(data.screenshots);
    });
    
    // New video event
    socket.on('new_video', function(video) {
        console.log('New video:', video);
        
        // Add video to list
        addVideo(video);
    });
    
    // Videos update event
    socket.on('videos_update', function(data) {
        console.log('Videos update:', data);
        
        // Update videos
        updateVideos(data.videos);
    });
    
    // Update screenshots display
    function updateScreenshots(screenshots) {
        if (!screenshots || screenshots.length === 0) {
            noScreenshots.style.display = 'block';
            screenshotsList.innerHTML = '';
            return;
        }
        
        noScreenshots.style.display = 'none';
        screenshotsList.innerHTML = '';
        
        // Add screenshots in reverse order (newest first)
        screenshots.slice().reverse().forEach(screenshot => {
            addScreenshot(screenshot);
        });
    }
    
    // Add screenshot to list
    function addScreenshot(screenshot) {
        // Hide no screenshots message
        noScreenshots.style.display = 'none';
        
        const screenshotItem = document.createElement('div');
        screenshotItem.className = 'screenshot-item';
        
        const timestamp = document.createElement('div');
        timestamp.className = 'timestamp';
        timestamp.textContent = screenshot.timestamp;
        
        const img = document.createElement('img');
        img.src = 'data:image/png;base64,' + screenshot.data;
        img.alt = 'Browser Screenshot';
        
        screenshotItem.appendChild(timestamp);
        screenshotItem.appendChild(img);
        
        // Add to beginning of list
        screenshotsList.insertBefore(screenshotItem, screenshotsList.firstChild);
    }
    
    // Update videos display
    function updateVideos(videos) {
        if (!videos || videos.length === 0) {
            noVideos.style.display = 'block';
            videosList.innerHTML = '';
            return;
        }
        
        noVideos.style.display = 'none';
        videosList.innerHTML = '';
        
        // Add videos in reverse order (newest first)
        videos.slice().reverse().forEach(video => {
            addVideo(video);
        });
    }
    
    // Add video to list
    function addVideo(video) {
        // Hide no videos message
        noVideos.style.display = 'none';
        
        const videoItem = document.createElement('div');
        videoItem.className = 'video-item';
        
        const timestamp = document.createElement('div');
        timestamp.className = 'timestamp';
        timestamp.textContent = video.timestamp;
        
        const videoElement = document.createElement('video');
        videoElement.src = 'data:video/webm;base64,' + video.data;
        videoElement.controls = true;
        videoElement.autoplay = false;
        videoElement.muted = true;
        videoElement.alt = 'Browser Recording';
        
        videoItem.appendChild(timestamp);
        videoItem.appendChild(videoElement);
        
        // Add to beginning of list
        videosList.insertBefore(videoItem, videosList.firstChild);
    }
    
    // Update results display
    function updateResults(results) {
        if (!results) {
            noResults.style.display = 'block';
            resultsList.innerHTML = '';
            return;
        }
        
        noResults.style.display = 'none';
        
        // Format and display results
        if (typeof results === 'object') {
            resultsList.textContent = JSON.stringify(results, null, 2);
        } else {
            resultsList.textContent = results;
        }
    }
    
    // Helper function to capitalize first letter
    function capitalizeFirstLetter(string) {
        return string.charAt(0).toUpperCase() + string.slice(1);
    }
});
