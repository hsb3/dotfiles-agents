import { Plugin, Notice } from 'obsidian';

/**
 * Minimal Obsidian Plugin Example
 *
 * Demonstrates the essential structure of an Obsidian plugin with:
 * - Basic lifecycle methods
 * - Command registration
 * - Simple settings
 */

interface MinimalSettings {
  greeting: string;
}

const DEFAULT_SETTINGS: MinimalSettings = {
  greeting: 'Hello from Obsidian!',
};

export default class MinimalPlugin extends Plugin {
  settings: MinimalSettings;

  async onload() {
    console.debug('Minimal plugin loading...');

    // Load settings
    await this.loadSettings();

    // Add a simple command
    this.addCommand({
      id: 'show-greeting',
      name: 'Show greeting',
      callback: () => {
        new Notice(this.settings.greeting);
      }
    });

    // Add ribbon icon
    this.addRibbonIcon('smile', 'Show greeting', () => {
      new Notice(this.settings.greeting);
    });

    console.debug('Minimal plugin loaded');
  }

  async onunload() {
    console.debug('Minimal plugin unloaded');
  }

  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings() {
    await this.saveData(this.settings);
  }
}
