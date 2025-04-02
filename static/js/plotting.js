class PlottingTab {
    constructor() {
        this.selectedFile = null;
        this.selectedPlot = null;
        this.availablePlots = [];
        this.plotParameters = {};
        this.plotDiv = document.getElementById('plot-container');
        this.setupEventListeners();
        this.loadAvailablePlots();
        this.populateFileSelector();
    }

    setupEventListeners() {
        // File selection
        document.getElementById('plot-file-select').addEventListener('change', (e) => {
            this.selectedFile = e.target.value;
            this.loadAvailableData();
        });

        // Plot selection
        document.getElementById('plot-select').addEventListener('change', (e) => {
            this.selectedPlot = e.target.value;
            this.updatePlot();
        });
    }

    async populateFileSelector() {
        try {
            const response = await fetch('/api/files/');
            const data = await response.json();
            const select = document.getElementById('plot-file-select');
            
            if (!select) {
                console.error('Plot file select element not found!');
                return;
            }
            
            select.innerHTML = '<option value="">Choose a file...</option>';
            
            if (!data.files || data.files.length === 0) {
                console.log('No files to populate in selector');
                return;
            }
            
            data.files.forEach(file => {
                const option = document.createElement('option');
                option.value = file.filepath;
                option.textContent = `${file.filename} (${file.classification || 'Uncategorized'})`;
                select.appendChild(option);
            });
        } catch (error) {
            console.error('Error populating file selector:', error);
        }
    }

    async loadAvailablePlots() {
        try {
            const response = await fetch('/api/plots');
            const data = await response.json();
            this.availablePlots = data.plots;
            this.populatePlotSelect();
        } catch (error) {
            console.error('Error loading available plots:', error);
            alert('Error loading available plots. Please try again.');
        }
    }

    populatePlotSelect() {
        const select = document.getElementById('plot-select');
        select.innerHTML = '<option value="">Choose a plot type...</option>';
        
        this.availablePlots.forEach(plot => {
            const option = document.createElement('option');
            option.value = plot.name;
            option.textContent = plot.display_name;
            option.title = plot.description;
            select.appendChild(option);
        });
    }

    async loadAvailableData() {
        if (!this.selectedFile) return;

        try {
            // Load marker names
            const markerResponse = await fetch(`/api/plot/${encodeURIComponent(this.selectedFile)}/markers`);
            const markerData = await markerResponse.json();
            if (markerData && markerData.markers) {
                this.populateMarkerSelect(markerData.markers);
            } else {
                console.error('Invalid marker data format:', markerData);
                this.populateMarkerSelect([]);
            }

            // Load channel names
            const channelResponse = await fetch(`/api/plot/${encodeURIComponent(this.selectedFile)}/channels`);
            const channelData = await channelResponse.json();
            if (channelData && channelData.channels) {
                this.populateChannelSelect(channelData.channels);
            } else {
                console.error('Invalid channel data format:', channelData);
                this.populateChannelSelect([]);
            }

            // Update plot if one is selected
            if (this.selectedPlot) {
                this.updatePlot();
            }
        } catch (error) {
            console.error('Error loading data:', error);
            alert('Error loading data. Please try again.');
            this.populateMarkerSelect([]);
            this.populateChannelSelect([]);
        }
    }

    populateMarkerSelect(markers) {
        const select = document.getElementById('marker-select');
        select.innerHTML = '';
        markers.forEach(marker => {
            const option = document.createElement('option');
            option.value = marker;
            option.textContent = marker;
            select.appendChild(option);
        });
    }

    populateChannelSelect(channels) {
        const select = document.getElementById('channel-select');
        select.innerHTML = '';
        channels.forEach(channel => {
            const option = document.createElement('option');
            option.value = channel;
            option.textContent = channel;
            select.appendChild(option);
        });
    }

    async updatePlot() {
        if (!this.selectedFile || !this.selectedPlot) return;

        try {
            // Get selected markers and channels
            const selectedMarkers = Array.from(document.getElementById('marker-select').selectedOptions, option => option.value);
            const selectedChannels = Array.from(document.getElementById('channel-select').selectedOptions, option => option.value);

            // Prepare parameters based on plot type
            const parameters = {};
            if (this.selectedPlot === 'MarkerTrajectoryPlot') {
                parameters.markers = selectedMarkers;
            } else if (this.selectedPlot === 'AnalogChannelPlot') {
                parameters.channels = selectedChannels;
            }

            // Get plot data
            const response = await fetch(
                `/api/plot/${encodeURIComponent(this.selectedFile)}?plot_name=${encodeURIComponent(this.selectedPlot)}&parameters=${encodeURIComponent(JSON.stringify(parameters))}`
            );
            const data = await response.json();
            
            // Update the plot
            Plotly.newPlot(this.plotDiv, data.traces, data.layout, data.config);
        } catch (error) {
            console.error('Error updating plot:', error);
            alert('Error updating plot. Please try again.');
        }
    }
}

// Initialize the plotting tab when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.plottingTab = new PlottingTab();
}); 