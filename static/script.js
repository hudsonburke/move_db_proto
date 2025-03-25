new Vue({
    el: '#app',
    data: {
        directoryPath: '',
        directoryStatus: '',
        searchFilters: {
            filename: { value: '', use_regex: false },
            classification: { value: '', use_regex: false },
            subject: { value: '', use_regex: false },
            session_name: { value: '', use_regex: false },
            min_duration: null,
            max_duration: null,
            min_frame_count: null,
            max_frame_count: null,
            marker: { value: '', use_regex: false },
            channel: { value: '', use_regex: false },
            event: { value: '', use_regex: false },
            analysis_name: '',
            analysis_params: '{}'
        },
        classifications: [],
        subjects: [],
        sessions: [],
        analyses: [],
        groups: [],
        selectedAnalysis: null,
        selectedClassification: '',
        selectedSubject: '',
        selectedSession: '',
        files: [],
        fileTree: {},
        fileCountInfo: '',
        loading: false,
        filterGroups: {
            basic: true,
            content: true,
            analysis: false
        },
        
        // Selection and group management
        selectedFiles: [],
        selectAllFiles: false,
        selectedGroupId: null,
        newGroup: {
            name: '',
            description: ''
        },
        editingGroupId: null,
        currentGroup: null,
        groupFiles: []
    },
    computed: {
        parsedAnalysisParams: {
            get() {
                try {
                    return JSON.parse(this.searchFilters.analysis_params);
                } catch (e) {
                    return {};
                }
            },
            set(value) {
                this.searchFilters.analysis_params = JSON.stringify(value);
            }
        }
    },
    methods: {
        initializeComponents() {
            this.fileDetailsModal = new bootstrap.Modal(document.getElementById('fileDetailsModal'));
            this.addToGroupModal = new bootstrap.Modal(document.getElementById('addToGroupModal'));
            this.createGroupModal = new bootstrap.Modal(document.getElementById('createGroupModal'));
            this.groupFilesModal = new bootstrap.Modal(document.getElementById('groupFilesModal'));
        },
        handleDirectoryScan() {
            if (!this.directoryPath) {
                this.directoryStatus = '<div class="alert alert-warning">Please enter a directory path</div>';
                return;
            }
            this.directoryStatus = '<div class="d-flex align-items-center"><div class="spinner-border spinner-border-sm me-2" role="status"></div>Scanning directory (this will run in the background)...</div>';
            fetch(`/api/directory-scan`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ root_directory: this.directoryPath })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                // For background tasks, show a success message that the scan has started
                if (data.status === "processing") {
                    this.directoryStatus = '<div class="alert alert-info">' + data.detail + 
                        ' <br><small>Files will appear in searches once processing is complete.</small></div>';
                    
                    // Set a timer to refresh the classifications after a delay to allow for processing
                    setTimeout(() => {
                        this.loadClassifications();
                        this.searchFiles();
                    }, 5000); // Try checking after 5 seconds
                } else {
                    // Handle case when old API endpoint is still being used
                    this.directoryStatus = `<div class="alert alert-success">Successfully indexed ${data.indexed?.length || 0} files</div>`;
                    this.loadClassifications();
                    this.searchFiles();
                }
                
                this.selectedClassification = '';
                this.selectedSubject = '';
                this.selectedSession = '';
            })
            .catch(error => {
                this.directoryStatus = `<div class="alert alert-danger">Directory scanning failed: ${error.message}</div>`;
            });
        },
        loadClassifications() {
            fetch(`/api/classifications/`)
            .then(response => response.json())
            .then(data => {
                this.classifications = data.classifications;
            })
            .catch(error => {
                console.error("Error loading classifications:", error);
            });
        },
        loadSubjects() {
            fetch(`/api/subjects/?classification=${encodeURIComponent(this.selectedClassification)}`)
            .then(response => response.json())
            .then(data => {
                this.subjects = data.subjects;
                this.selectedSubject = '';
                this.selectedSession = '';
                this.sessions = [];
                this.searchFiles();
            })
            .catch(error => {
                console.error("Error loading subjects:", error);
            });
        },
        loadSessions() {
            fetch(`/api/sessions/?classification=${encodeURIComponent(this.selectedClassification)}&subject=${encodeURIComponent(this.selectedSubject)}`)
            .then(response => response.json())
            .then(data => {
                this.sessions = data.sessions;
                this.selectedSession = '';
                this.searchFiles();
            })
            .catch(error => {
                console.error("Error loading sessions:", error);
            });
        },
        loadAnalyses() {
            fetch(`/api/analyses/`)
                .then(response => response.json())
                .then(data => {
                    this.analyses = data.analyses;
                })
                .catch(error => {
                    console.error("Error loading analyses:", error);
                });
        },
        loadGroups() {
            this.loading = true;
            fetch('/api/groups/')
                .then(response => response.json())
                .then(data => {
                    this.groups = data;
                    this.loading = false;
                })
                .catch(error => {
                    console.error("Error loading groups:", error);
                    this.loading = false;
                });
        },
        onAnalysisChange() {
            if (this.searchFilters.analysis_name) {
                const selectedAnalysis = this.analyses.find(a => a.name === this.searchFilters.analysis_name);
                if (selectedAnalysis) {
                    this.selectedAnalysis = selectedAnalysis;
                    
                    // Initialize default parameter values
                    const defaultParams = {};
                    for (const [key, type] of Object.entries(selectedAnalysis.parameters)) {
                        if (type === 'int' || type === int) {
                            defaultParams[key] = 0;
                        } else if (type === 'float' || type === float) {
                            defaultParams[key] = 0.0;
                        } else if (type === 'str' || type === String || type === str) {
                            defaultParams[key] = '';
                        } else if (type === 'bool' || type === bool) {
                            defaultParams[key] = false;
                        }
                    }
                    this.parsedAnalysisParams = defaultParams;
                }
            } else {
                this.selectedAnalysis = null;
                this.parsedAnalysisParams = {};
            }
        },
        updateAnalysisParam(key, value) {
            const params = this.parsedAnalysisParams;
            params[key] = value;
            this.parsedAnalysisParams = params;
        },
        buildFileTree(files) {
            // Create tree structure
            const tree = {};
            
            files.forEach(file => {
                const classification = file.classification || 'Uncategorized';
                const subject = file.subject_name || 'Unknown';
                const session = file.session_name || 'Default';
                
                // Initialize structure if needed
                if (!tree[classification]) {
                    tree[classification] = { subjects: {} };
                }
                
                if (!tree[classification].subjects[subject]) {
                    tree[classification].subjects[subject] = { sessions: {} };
                }
                
                if (!tree[classification].subjects[subject].sessions[session]) {
                    tree[classification].subjects[subject].sessions[session] = { files: [] };
                }
                
                // Add file to the appropriate place in the tree
                tree[classification].subjects[subject].sessions[session].files.push(file);
            });
            
            return tree;
        },
        toggleRegex(field) {
            if (this.searchFilters[field]) {
                this.searchFilters[field].use_regex = !this.searchFilters[field].use_regex;
            }
        },
        searchFiles() {
            this.loading = true;
            const params = new URLSearchParams();
            
            // Add basic metadata filters with individual regex flags
            if (this.searchFilters.filename.value) {
                params.append('filename', this.searchFilters.filename.value);
                if (this.searchFilters.filename.use_regex) {
                    params.append('filename_regex', 'true');
                }
            }
            
            if (this.searchFilters.classification.value || this.selectedClassification) {
                params.append('classification', this.searchFilters.classification.value || this.selectedClassification);
                if (this.searchFilters.classification.use_regex && !this.selectedClassification) {
                    params.append('classification_regex', 'true');
                }
            }
            
            if (this.searchFilters.subject.value || this.selectedSubject) {
                params.append('subject', this.searchFilters.subject.value || this.selectedSubject);
                if (this.searchFilters.subject.use_regex && !this.selectedSubject) {
                    params.append('subject_regex', 'true');
                }
            }
            
            if (this.searchFilters.session_name.value || this.selectedSession) {
                params.append('session_name', this.searchFilters.session_name.value || this.selectedSession);
                if (this.searchFilters.session_name.use_regex && !this.selectedSession) {
                    params.append('session_regex', 'true');
                }
            }
            
            // Add numeric range filters
            if (this.searchFilters.min_duration !== null) params.append('min_duration', this.searchFilters.min_duration);
            if (this.searchFilters.max_duration !== null) params.append('max_duration', this.searchFilters.max_duration);
            if (this.searchFilters.min_frame_count !== null) params.append('min_frame_count', this.searchFilters.min_frame_count);
            if (this.searchFilters.max_frame_count !== null) params.append('max_frame_count', this.searchFilters.max_frame_count);
            
            // Add content filters with individual regex flags
            if (this.searchFilters.marker.value) {
                params.append('marker', this.searchFilters.marker.value);
                if (this.searchFilters.marker.use_regex) {
                    params.append('marker_regex', 'true');
                }
            }
            
            if (this.searchFilters.channel.value) {
                params.append('channel', this.searchFilters.channel.value);
                if (this.searchFilters.channel.use_regex) {
                    params.append('channel_regex', 'true');
                }
            }
            
            if (this.searchFilters.event.value) {
                params.append('event', this.searchFilters.event.value);
                if (this.searchFilters.event.use_regex) {
                    params.append('event_regex', 'true');
                }
            }
            
            // Add analysis filters
            if (this.searchFilters.analysis_name) {
                params.append('analysis_name', this.searchFilters.analysis_name);
                
                // Only pass params if valid JSON
                try {
                    const analysisParams = JSON.parse(this.searchFilters.analysis_params);
                    if (analysisParams && typeof analysisParams === 'object') {
                        params.append('analysis_params', this.searchFilters.analysis_params);
                    }
                } catch (e) {
                    console.error("Invalid analysis parameters JSON:", e);
                }
            }
            
            params.append('limit', 10000);
            
            console.log('Fetching files with params:', params.toString());  // Add logging
            fetch(`/api/files/?${params.toString()}`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! Status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    this.files = data.files || [];
                    this.selectedFiles = [];  // Clear selected files
                    this.selectAllFiles = false;  // Reset select all checkbox
                    this.fileTree = this.buildFileTree(this.files);
                    this.fileCountInfo = `Total: ${data.pagination?.filtered || 0} of ${data.pagination?.total || 0} files`;
                    console.log('Files loaded:', this.files.length);
                })
                .catch(error => {
                    console.error(`Error loading files: ${error.message}`);
                    this.fileTree = {};
                    this.files = [];
                    this.fileCountInfo = "Error loading files";
                })
                .finally(() => {
                    this.loading = false;  // Always turn off loading state
                });
        },
        clearSearchForm() {
            this.searchFilters = {
                filename: { value: '', use_regex: false },
                classification: { value: '', use_regex: false },
                subject: { value: '', use_regex: false },
                session_name: { value: '', use_regex: false },
                min_duration: null,
                max_duration: null,
                min_frame_count: null,
                max_frame_count: null,
                marker: { value: '', use_regex: false },
                channel: { value: '', use_regex: false },
                event: { value: '', use_regex: false },
                analysis_name: '',
                analysis_params: '{}'
            };
            this.selectedAnalysis = null;
            this.selectedClassification = '';
            this.selectedSubject = '';
            this.selectedSession = '';
            this.loadClassifications();
            this.searchFiles();
        },
        toggleFilterGroup(groupName) {
            // Fix for collapsible filters
            Vue.set(this.filterGroups, groupName, !this.filterGroups[groupName]);
        },
        showFileDetails(fileId) {
            const modalTitle = document.getElementById('fileDetailsTitle');
            const modalBody = document.getElementById('fileDetailsBody');
            const downloadBtn = document.getElementById('downloadFileBtn');
            modalTitle.innerText = 'Loading...';
            modalBody.innerHTML = `
                <div class="text-center">
                    <div class="spinner-border" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </div>
            `;
            downloadBtn.style.display = 'none';
            
            this.fileDetailsModal.show();
            fetch(`/api/files/${fileId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(file => {
                modalTitle.innerText = file.filename;
                const markerBadges = file.markers.map(m => 
                    `<span class="badge bg-secondary marker-badge">${m.marker_name}</span>`
                ).join('');
                const channelBadges = file.channels.map(c => 
                    `<span class="badge bg-info channel-badge">${c.channel_name}</span>`
                ).join('');
                const eventBadges = file.events.map(e => 
                    `<span class="badge bg-warning event-badge">${e.event_name} (${e.event_time !== undefined ? e.event_time.toFixed(2) : '0.00'}s)</span>`
                ).join('');
                const classification = file.classification || 'Uncategorized';
                const subject = file.subject_name || 'Unknown';
                const session = file.session_name || 'Default';
                const hierarchyPath = `
                    <div class="tree-path">
                        <i class="bi bi-diagram-3"></i> 
                        <strong>${classification}</strong> / 
                        <strong>${subject}</strong> / 
                        <strong>${session}</strong> / 
                        ${file.filename}
                    </div>
                `;
                modalBody.innerHTML = `
                    ${hierarchyPath}
                    <div class="row">
                        <div class="col-md-6">
                            <p><strong>Classification:</strong> ${classification}</p>
                            <p><strong>Subject:</strong> ${subject}</p>
                            <p><strong>Session:</strong> ${session}</p>
                            <p><strong>Duration:</strong> ${file.duration !== undefined ? file.duration.toFixed(2) : '0.00'}s</p>
                            <p><strong>Frames:</strong> ${file.frame_count}</p>
                        </div>
                        <div class="col-md-6">
                            <p><strong>Sample Rate:</strong> ${file.sample_rate !== undefined ? file.sample_rate.toFixed(2) : '0.00'} Hz</p>
                            <p><strong>File Size:</strong> ${this.formatFileSize(file.file_size)}</p>
                            <p><strong>Date Added:</strong> ${new Date(file.date_added).toLocaleString()}</p>
                            <p><strong>Path:</strong> <span class="text-truncate d-block">${file.filepath}</span></p>
                        </div>
                    </div>
                    <div class="mt-4">
                        <h6>Markers (${file.markers.length}):</h6>
                        <div>${markerBadges || 'No markers'}</div>
                    </div>
                    <div class="mt-3">
                        <h6>Analog Channels (${file.channels.length}):</h6>
                        <div>${channelBadges || 'No channels'}</div>
                    </div>
                    <div class="mt-3">
                        <h6>Events (${file.events.length}):</h6>
                        <div>${eventBadges || 'No events'}</div>
                    </div>
                `;
                downloadBtn.style.display = 'block';
                downloadBtn.href = `/api/files/${fileId}/download`;
            })
            .catch(error => {
                modalBody.innerHTML = `<div class="alert alert-danger">Error loading file details: ${error.message}</div>`;
            });
        },
        deleteFile(fileId) {
            if (!confirm('Are you sure you want to delete this file? This action cannot be undone.')) {
                return;
            }
            fetch(`/api/files/${fileId}`, {
                method: 'DELETE'
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                this.showNotification('File deleted successfully');
                this.searchFiles();
            })
            .catch(error => {
                alert(`Error deleting file: ${error.message}`);
            });
        },
        formatFileSize(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        },
        
        // File selection methods
        toggleSelectFile(fileId) {
            const index = this.selectedFiles.indexOf(fileId);
            if (index === -1) {
                this.selectedFiles.push(fileId);
            } else {
                this.selectedFiles.splice(index, 1);
            }
        },
        toggleSelectAll() {
            if (this.selectAllFiles) {
                // Select all files
                this.selectedFiles = this.files.map(file => file.id);
            } else {
                // Deselect all files
                this.selectedFiles = [];
            }
        },
        clearSelection() {
            this.selectedFiles = [];
            this.selectAllFiles = false;
        },
        
        // Group management methods
        showAddToGroupModal() {
            if (this.selectedFiles.length === 0) {
                this.showNotification('Please select at least one file first', 'warning');
                return;
            }
            // Ensure we have the latest groups
            this.loadGroups();
            this.selectedGroupId = null;
            this.addToGroupModal.show();
        },
        addSelectedFilesToGroup() {
            if (!this.selectedGroupId || this.selectedFiles.length === 0) {
                return;
            }
            
            this.loading = true;
            fetch(`/api/groups/${this.selectedGroupId}/files`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(this.selectedFiles)
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                this.addToGroupModal.hide();
                this.showNotification(`Added ${this.selectedFiles.length} files to group`);
                this.clearSelection();
                this.loadGroups();
                this.loading = false;
            })
            .catch(error => {
                this.loading = false;
                this.showNotification(`Error adding files to group: ${error.message}`, 'danger');
            });
        },
        showCreateGroupModal() {
            this.newGroup = { name: '', description: '' };
            this.editingGroupId = null;
            this.createGroupModal.show();
        },
        showEditGroupModal(group) {
            this.newGroup = {
                name: group.name,
                description: group.description
            };
            this.editingGroupId = group.id;
            this.createGroupModal.show();
        },
        saveGroup() {
            if (!this.newGroup.name) {
                this.showNotification('Group name is required', 'warning');
                return;
            }
            
            this.loading = true;
            let url = '/api/groups/';
            let method = 'POST';
            let body = {
                name: this.newGroup.name,
                description: this.newGroup.description || ''
            };
            
            // If editing, use PUT request
            if (this.editingGroupId) {
                url = `/api/groups/${this.editingGroupId}`;
                method = 'PUT';
            }
            
            // If creating and we have selected files, add them to the new group
            if (!this.editingGroupId && this.selectedFiles.length > 0) {
                body.file_ids = this.selectedFiles;
            }
            
            fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(body)
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                this.createGroupModal.hide();
                this.showNotification(`Group ${this.editingGroupId ? 'updated' : 'created'} successfully`);
                this.loadGroups();
                
                // If we created a group with selected files, clear selection
                if (!this.editingGroupId && this.selectedFiles.length > 0) {
                    this.clearSelection();
                }
                
                this.loading = false;
            })
            .catch(error => {
                this.loading = false;
                this.showNotification(`Error ${this.editingGroupId ? 'updating' : 'creating'} group: ${error.message}`, 'danger');
            });
        },
        viewGroupFiles(groupId) {
            this.loading = true;
            this.currentGroup = this.groups.find(g => g.id === groupId);
            this.groupFiles = [];
            
            fetch(`/api/groups/${groupId}/files`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! Status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(files => {
                    this.groupFiles = files;
                    this.loading = false;
                    this.groupFilesModal.show();
                })
                .catch(error => {
                    this.loading = false;
                    this.showNotification(`Error loading group files: ${error.message}`, 'danger');
                });
        },
        deleteGroup(groupId) {
            if (!confirm('Are you sure you want to delete this group? This will not delete the files, only the group.')) {
                return;
            }
            
            this.loading = true;
            fetch(`/api/groups/${groupId}`, {
                method: 'DELETE'
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                this.showNotification('Group deleted successfully');
                this.loadGroups();
                this.loading = false;
            })
            .catch(error => {
                this.loading = false;
                this.showNotification(`Error deleting group: ${error.message}`, 'danger');
            });
        },
        removeFileFromGroup(fileId) {
            if (!this.currentGroup) return;
            
            if (!confirm('Remove this file from the group?')) {
                return;
            }
            
            this.loading = true;
            fetch(`/api/groups/${this.currentGroup.id}/files/${fileId}`, {
                method: 'DELETE'
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                // Remove file from the list
                this.groupFiles = this.groupFiles.filter(f => f.id !== fileId);
                this.loadGroups();  // Refresh group counts
                this.loading = false;
                this.showNotification('File removed from group');
            })
            .catch(error => {
                this.loading = false;
                this.showNotification(`Error removing file from group: ${error.message}`, 'danger');
            });
        },
        showNotification(message, type = 'success') {
            const notification = document.createElement('div');
            notification.className = 'position-fixed top-0 end-0 p-3';
            notification.style.zIndex = '1050';
            notification.innerHTML = `
                <div class="toast show" role="alert">
                    <div class="toast-header bg-${type} text-white">
                        <strong class="me-auto">Notification</strong>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
                    </div>
                    <div class="toast-body">
                        ${message}
                    </div>
                </div>
            `;
            document.body.appendChild(notification);
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 3000);
        },
        handleCreateFile() {
            const payload = {
                ...this.newFile,
                analyses: this.selectedAnalyses.map(a => a.id)  // Include selected analyses
            };
            fetch('/api/files/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                this.showNotification('File created successfully');
                this.loadFiles();
            })
            .catch(error => {
                this.showNotification(`Error creating file: ${error.message}`, 'danger');
            });
        },

        handleUpdateFile() {
            const payload = {
                ...this.editFile,
                analyses: this.selectedAnalyses.map(a => a.id)  // Include selected analyses
            };
            fetch(`/api/files/${this.editFile.id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                this.showNotification('File updated successfully');
                this.loadFiles();
            })
            .catch(error => {
                this.showNotification(`Error updating file: ${error.message}`, 'danger');
            });
        }
    },
    mounted() {
        this.initializeComponents();
        this.loadClassifications();
        this.loadAnalyses();
        this.loadGroups();
        this.searchFiles();
    }
});