"""
Configuration management for OCR Proofreading Application.

Handles loading and accessing application configuration from config.yaml.
"""

import os
from typing import Dict, List, Tuple, Any
import yaml


class Config:
    """
    Application configuration manager.
    
    Loads configuration from config.yaml and provides easy access to settings.
    """
    
    def __init__(self, config_path: str = None):
        """
        Initialize configuration.
        
        Parameters:
        config_path (str): Path to config.yaml file. If None, uses default location.
        """
        if config_path is None:
            # Default to config.yaml in repository root
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'config.yaml'
            )
        
        self.config_path = config_path
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from YAML file.
        
        Returns:
        dict: Configuration dictionary.
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            # Return default configuration if file not found
            return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """
        Return default configuration.
        
        Returns:
        dict: Default configuration dictionary.
        """
        return {
            'max_upload_size_mb': 700,
            'colors': {
                'matching_boxes': [0, 255, 0],
                'unverified_boxes': [255, 255, 0]
            },
            'bbox': {
                'line_width': 3,
                'selection_opacity': 0.15,
                'tolerance_pixels': 2,
                'critical_threshold_pixels': 20
            },
            'image': {
                'jp2_compression_level': 1
            }
        }
    
    @property
    def max_upload_size_mb(self) -> int:
        """Get maximum upload size in MB."""
        return self._config.get('max_upload_size_mb', 700)
    
    @property
    def max_upload_size_bytes(self) -> int:
        """Get maximum upload size in bytes."""
        return self.max_upload_size_mb * 1024 * 1024
    
    @property
    def matching_color(self) -> Tuple[int, int, int]:
        """Get color for matching bounding boxes (RGB)."""
        color = self._config.get('colors', {}).get('matching_boxes', [0, 255, 0])
        return tuple(color)
    
    @property
    def unverified_color(self) -> Tuple[int, int, int]:
        """Get color for unverified bounding boxes (RGB)."""
        color = self._config.get('colors', {}).get('unverified_boxes', [255, 255, 0])
        return tuple(color)
    
    @property
    def bbox_line_width(self) -> int:
        """Get bounding box line width."""
        return self._config.get('bbox', {}).get('line_width', 3)
    
    @property
    def bbox_selection_opacity(self) -> float:
        """Get bounding box selection opacity."""
        return self._config.get('bbox', {}).get('selection_opacity', 0.15)
    
    @property
    def bbox_tolerance(self) -> int:
        """Get bounding box tolerance in pixels."""
        return self._config.get('bbox', {}).get('tolerance_pixels', 2)
    
    @property
    def bbox_critical_threshold(self) -> int:
        """Get bounding box critical threshold in pixels."""
        return self._config.get('bbox', {}).get('critical_threshold_pixels', 20)
    
    @property
    def jp2_compression_level(self) -> int:
        """Get JP2 to PNG compression level."""
        return self._config.get('image', {}).get('jp2_compression_level', 1)


# Global configuration instance
_config_instance = None


def get_config() -> Config:
    """
    Get global configuration instance.
    
    Returns:
    Config: Global configuration object.
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance
