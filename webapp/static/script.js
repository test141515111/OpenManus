document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const taskForm = document.getElementById('taskForm');
    const taskInput = document.getElementById('taskInput');
    const submitBtn = document.getElementById('submitBtn');
    const taskStatus = document.getElementById('taskStatus');
    const currentTask = document.getElementById('currentTask');
    const resultContainer = document.getElementById('resultContainer');
    const resultContent = document.getElementById('resultContent');
    const noResults = document.getElementById('noResults');
    const screenshotsContainer = document.getElementById('screenshotsContainer');
    const screenshotsList = document.getElementById('screenshotsList');
    const noScreenshots = document.getElementById('noScreenshots');
    
    // Task status polling interval
    let pollingInterval = null;
    
    // Initialize Socket.IO if available
    let socket = null;
    try {
        socket = io();
        
        // Socket.IO event handlers
        socket.on('connect', function() {
            console.log('Socket.IO connected');
        });
        
        socket.on('disconnect', function() {
            console.log('Socket.IO disconnected');
        });
        
        socket.on('status_update', function(data) {
            updateTaskStatus(data);
        });
        
        socket.on('error', function(data) {
            showError(data.message);
        });
        
        console.log('Socket.IO initialized');
    } catch (e) {
        console.error('Socket.IO initialization failed:', e);
        socket = null;
    }
    
    // Form submission handler
    taskForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Get the task from the input
        const query = taskInput.value.trim();
        
        if (!query) {
            showError('タスクを入力してください');
            return;
        }
        
        // Disable the submit button
        submitBtn.disabled = true;
        
        // Update the task status
        taskStatus.textContent = '実行中';
        currentTask.textContent = query;
        
        // Clear the result and screenshots
        noResults.style.display = 'block';
        resultContent.innerHTML = '';
        noScreenshots.style.display = 'block';
        screenshotsList.innerHTML = '';
        
        // Submit the task
        submitTask(query);
    });
    
    // Submit task function
    function submitTask(query) {
        if (socket && socket.connected) {
            // Submit task via Socket.IO
            console.log('Submitting task via Socket.IO:', query);
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
                if (data.status === 'error') {
                    showError(data.message);
                    submitBtn.disabled = false;
                } else {
                    // Start polling for task status
                    startPolling();
                }
            })
            .catch(error => {
                showError('タスクの送信中にエラーが発生しました: ' + error.message);
                submitBtn.disabled = false;
            });
        }
    }
    
    // Update task status function
    function updateTaskStatus(data) {
        // Update the task status
        taskStatus.textContent = getStatusText(data.status);
        currentTask.textContent = data.current_task || 'なし';
        
        // Update the result
        if (data.result) {
            noResults.style.display = 'none';
            resultContent.innerHTML = formatResult(data.result);
        } else {
            noResults.style.display = 'block';
            resultContent.innerHTML = '';
        }
        
        // Update the screenshots
        if (data.screenshots && data.screenshots.length > 0) {
            noScreenshots.style.display = 'none';
            screenshotsList.innerHTML = '';
            
            data.screenshots.forEach(function(screenshot) {
                const img = document.createElement('img');
                img.src = screenshot;
                img.alt = 'スクリーンショット';
                img.className = 'img-fluid mb-3';
                screenshotsList.appendChild(img);
            });
        } else {
            noScreenshots.style.display = 'block';
            screenshotsList.innerHTML = '';
        }
        
        // Enable the submit button if the task is completed or failed
        if (data.status === 'completed' || data.status === 'error') {
            submitBtn.disabled = false;
            
            // Stop polling
            if (pollingInterval) {
                clearInterval(pollingInterval);
                pollingInterval = null;
            }
        }
    }
    
    // Format result function
    function formatResult(result) {
        if (typeof result === 'string') {
            return '<p>' + result.replace(/\n/g, '<br>') + '</p>';
        } else if (typeof result === 'object') {
            return '<pre>' + JSON.stringify(result, null, 2) + '</pre>';
        } else {
            return '<p>' + result + '</p>';
        }
    }
    
    // Get status text function
    function getStatusText(status) {
        switch (status) {
            case 'idle':
                return '待機中';
            case 'running':
                return '実行中';
            case 'completed':
                return '完了';
            case 'error':
                return 'エラー';
            default:
                return status;
        }
    }
    
    // Show error function
    function showError(message) {
        alert('エラー: ' + message);
    }
    
    // Start polling function
    function startPolling() {
        if (pollingInterval) clearInterval(pollingInterval);
        
        pollingInterval = setInterval(function() {
            fetch('/api/task_status')
                .then(response => response.json())
                .then(data => {
                    updateTaskStatus(data);
                })
                .catch(error => {
                    console.error('Error polling task status:', error);
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
            console.error('Error checking initial task status:', error);
        });
});
