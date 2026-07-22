import { App, Plugin, PluginSettingTab, Setting, Notice } from 'obsidian';

/**
 * Complete Settings Implementation Example
 *
 * Demonstrates:
 * - Settings interface with typed fields
 * - Default values and merge pattern
 * - PluginSettingTab with all common control types
 * - Settings validation
 * - Conditional settings display
 */

// --- Settings Interface ---

interface MyPluginSettings {
  // Connection
  serverUrl: string;
  apiKey: string;
  port: number;

  // Behavior
  enabled: boolean;
  autoSync: boolean;
  syncInterval: number; // minutes

  // Content
  outputFolder: string;
  template: string;
  maxResults: number;

  // Appearance
  theme: 'light' | 'dark' | 'auto';
  fontSize: number;
}

const DEFAULT_SETTINGS: MyPluginSettings = {
  serverUrl: 'http://localhost:3000',
  apiKey: '',
  port: 3000,
  enabled: true,
  autoSync: false,
  syncInterval: 5,
  outputFolder: 'output',
  template: '# {{title}}\n\n{{content}}',
  maxResults: 50,
  theme: 'auto',
  fontSize: 14,
};

// --- Plugin Class ---

export default class MyPlugin extends Plugin {
  settings: MyPluginSettings;

  async onload() {
    await this.loadSettings();
    this.addSettingTab(new MyPluginSettingTab(this.app, this));

    // Use settings in commands
    this.addCommand({
      id: 'show-settings-status',
      name: 'Show connection status',
      callback: () => {
        const status = this.settings.enabled
          ? `Connected to ${this.settings.serverUrl}`
          : 'Plugin disabled';
        new Notice(status);
      },
    });
  }

  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings() {
    await this.saveData(this.settings);
  }
}

// --- Settings Tab ---

class MyPluginSettingTab extends PluginSettingTab {
  plugin: MyPlugin;

  constructor(app: App, plugin: MyPlugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  display(): void {
    const { containerEl } = this;
    containerEl.empty();

    // --- Connection Section ---

    new Setting(containerEl).setName('Connection').setHeading();

    new Setting(containerEl)
      .setName('Server URL')
      .setDesc('The URL of the backend server.')
      .addText((text) =>
        text
          .setPlaceholder('http://localhost:3000')
          .setValue(this.plugin.settings.serverUrl)
          .onChange(async (value) => {
            this.plugin.settings.serverUrl = value;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName('API key')
      .setDesc('Your API authentication key.')
      .addText((text) => {
        text
          .setPlaceholder('Enter your API key')
          .setValue(this.plugin.settings.apiKey)
          .onChange(async (value) => {
            this.plugin.settings.apiKey = value;
            await this.plugin.saveSettings();
          });
        // Make it a password field
        text.inputEl.type = 'password';
      });

    new Setting(containerEl)
      .setName('Port')
      .setDesc('Server port number (1024-65535).')
      .addText((text) =>
        text
          .setPlaceholder('3000')
          .setValue(String(this.plugin.settings.port))
          .onChange(async (value) => {
            const port = parseInt(value, 10);
            if (!isNaN(port) && port >= 1024 && port <= 65535) {
              this.plugin.settings.port = port;
              await this.plugin.saveSettings();
            }
          })
      );

    // Test connection button
    new Setting(containerEl)
      .setName('Test connection')
      .setDesc('Verify the server is reachable.')
      .addButton((btn) =>
        btn
          .setButtonText('Test')
          .setCta()
          .onClick(async () => {
            btn.setDisabled(true);
            btn.setButtonText('Testing...');
            try {
              // Replace with actual connection test
              await new Promise((resolve) => setTimeout(resolve, 1000));
              new Notice('Connection successful');
            } catch {
              new Notice('Connection failed');
            } finally {
              btn.setDisabled(false);
              btn.setButtonText('Test');
            }
          })
      );

    // --- Behavior Section ---

    new Setting(containerEl).setName('Behavior').setHeading();

    new Setting(containerEl)
      .setName('Enable plugin')
      .setDesc('Toggle the plugin on or off.')
      .addToggle((toggle) =>
        toggle.setValue(this.plugin.settings.enabled).onChange(async (value) => {
          this.plugin.settings.enabled = value;
          await this.plugin.saveSettings();
          // Re-render to show/hide conditional settings
          this.display();
        })
      );

    // Conditional settings: only show when enabled
    if (this.plugin.settings.enabled) {
      new Setting(containerEl)
        .setName('Auto sync')
        .setDesc('Automatically sync content at regular intervals.')
        .addToggle((toggle) =>
          toggle
            .setValue(this.plugin.settings.autoSync)
            .onChange(async (value) => {
              this.plugin.settings.autoSync = value;
              await this.plugin.saveSettings();
              this.display();
            })
        );

      if (this.plugin.settings.autoSync) {
        new Setting(containerEl)
          .setName('Sync interval')
          .setDesc('How often to sync (in minutes).')
          .addSlider((slider) =>
            slider
              .setLimits(1, 60, 1)
              .setValue(this.plugin.settings.syncInterval)
              .setDynamicTooltip()
              .onChange(async (value) => {
                this.plugin.settings.syncInterval = value;
                await this.plugin.saveSettings();
              })
          );
      }
    }

    // --- Content Section ---

    new Setting(containerEl).setName('Content').setHeading();

    new Setting(containerEl)
      .setName('Output folder')
      .setDesc('Folder where generated files are saved.')
      .addText((text) =>
        text
          .setPlaceholder('output')
          .setValue(this.plugin.settings.outputFolder)
          .onChange(async (value) => {
            this.plugin.settings.outputFolder = value;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName('Template')
      .setDesc('Template for generated content. Use {{title}} and {{content}} placeholders.')
      .addTextArea((textarea) => {
        textarea
          .setPlaceholder('# {{title}}\n\n{{content}}')
          .setValue(this.plugin.settings.template)
          .onChange(async (value) => {
            this.plugin.settings.template = value;
            await this.plugin.saveSettings();
          });
        textarea.inputEl.rows = 6;
        textarea.inputEl.cols = 40;
      });

    new Setting(containerEl)
      .setName('Max results')
      .setDesc('Maximum number of results to return (10-500).')
      .addSlider((slider) =>
        slider
          .setLimits(10, 500, 10)
          .setValue(this.plugin.settings.maxResults)
          .setDynamicTooltip()
          .onChange(async (value) => {
            this.plugin.settings.maxResults = value;
            await this.plugin.saveSettings();
          })
      );

    // --- Appearance Section ---

    new Setting(containerEl).setName('Appearance').setHeading();

    new Setting(containerEl)
      .setName('Theme')
      .setDesc('Color theme for the plugin UI.')
      .addDropdown((dropdown) =>
        dropdown
          .addOption('auto', 'Auto (follow Obsidian)')
          .addOption('light', 'Light')
          .addOption('dark', 'Dark')
          .setValue(this.plugin.settings.theme)
          .onChange(async (value) => {
            this.plugin.settings.theme = value as 'light' | 'dark' | 'auto';
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName('Font size')
      .setDesc('Font size in pixels for the plugin view.')
      .addSlider((slider) =>
        slider
          .setLimits(10, 24, 1)
          .setValue(this.plugin.settings.fontSize)
          .setDynamicTooltip()
          .onChange(async (value) => {
            this.plugin.settings.fontSize = value;
            await this.plugin.saveSettings();
          })
      );

    // --- Reset Section ---

    new Setting(containerEl).setName('Advanced').setHeading();

    new Setting(containerEl)
      .setName('Reset settings')
      .setDesc('Restore all settings to their default values.')
      .addButton((btn) =>
        btn
          .setButtonText('Reset')
          .setWarning()
          .onClick(async () => {
            this.plugin.settings = Object.assign({}, DEFAULT_SETTINGS);
            await this.plugin.saveSettings();
            this.display();
            new Notice('Settings reset to defaults');
          })
      );
  }
}
