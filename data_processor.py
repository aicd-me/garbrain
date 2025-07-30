#!/usr/bin/env python3
"""
Data processor for Garbicz Festival knowledge base.
Reads markdown files, standardizes data, and outputs JSON for Qdrant ingestion.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime


class GarbiczDataProcessor:
    def __init__(self):
        self.locations = self._load_locations()
        self.processed_data = []
        
    def _load_locations(self) -> Dict[str, Dict[str, Any]]:
        """Parse locations.md to build a location lookup dictionary."""
        locations = {}
        locations_file = Path("locations.md")
        
        if not locations_file.exists():
            print("Warning: locations.md not found")
            return locations
            
        with open(locations_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Parse location entries
        pattern = r'\*\s*\*\*(.*?)\*\*:\s*\[Open on Google Maps\]\(https://www\.google\.com/maps\?q=([\d.]+),([\d.]+)\)'
        matches = re.findall(pattern, content)
        
        for match in matches:
            name = match[0].strip()
            lat = float(match[1])
            lon = float(match[2])
            
            # Store with main name and alternatives
            locations[name.lower()] = {
                "name": name,
                "coordinates": {"lat": lat, "lon": lon}
            }
            
            # Add alternative names
            if "(" in name and ")" in name:
                alt_name = re.search(r'\((.*?)\)', name).group(1)
                locations[alt_name.lower()] = locations[name.lower()]
                
        return locations
        
    def _get_location_info(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract location information from text."""
        text_lower = text.lower()
        
        for loc_key, loc_info in self.locations.items():
            if loc_key in text_lower:
                return {
                    "name": loc_info["name"],
                    "coordinates": loc_info["coordinates"]
                }
        return None
        
    def _extract_keywords(self, text: str, category: str) -> List[str]:
        """Extract relevant keywords from text based on category."""
        keywords = []
        
        # Common festival keywords
        common_keywords = ["festival", "garbicz", "event", "music", "art", "culture"]
        
        # Category-specific keywords
        category_keywords = {
            "faq": ["tickets", "camping", "rules", "access", "payment", "safety"],
            "gastronomy": ["food", "drinks", "vegan", "vegetarian", "bar", "restaurant"],
            "timetable": ["dj", "performance", "stage", "schedule", "time", "day"],
            "workshops": ["workshop", "learning", "activity", "participation", "facilitator"],
            "general": ["information", "guide", "tips", "advice", "overview"],
            "locations": ["map", "stage", "area", "zone", "camping", "service"]
        }
        
        # Extract from text
        text_lower = text.lower()
        
        # Add category keywords if present in text
        if category.lower() in category_keywords:
            for keyword in category_keywords[category.lower()]:
                if keyword in text_lower:
                    keywords.append(keyword)
                    
        # Add location names as keywords
        location_info = self._get_location_info(text)
        if location_info:
            keywords.append(location_info["name"].lower())
            
        # Remove duplicates and return
        return list(set(keywords))[:5]  # Limit to 5 keywords
        
    def process_faq_file(self, filepath: Path) -> List[Dict[str, Any]]:
        """Process FAQ markdown file."""
        documents = []
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Split by ## headers (questions)
        sections = re.split(r'^##\s+', content, flags=re.MULTILINE)[1:]
        
        for section in sections:
            lines = section.strip().split('\n')
            if not lines:
                continue
                
            question = lines[0].strip()
            answer = '\n'.join(lines[1:]).strip()
            
            if not answer:
                continue
                
            doc = {
                "text": f"Q: {question}\nA: {answer}",
                "meta": {
                    "category": "FAQ",
                    "topic": question,
                    "type": "general info",
                    "keywords": self._extract_keywords(f"{question} {answer}", "faq")
                }
            }
            
            # Add location if mentioned
            location_info = self._get_location_info(f"{question} {answer}")
            if location_info:
                doc["meta"]["location"] = location_info
                
            documents.append(doc)
            
        return documents
        
    def process_gastro_file(self, filepath: Path) -> List[Dict[str, Any]]:
        """Process gastronomy highlights file."""
        documents = []
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Split by ### headers (food places)
        sections = re.split(r'^###\s+', content, flags=re.MULTILINE)[1:]
        
        for section in sections:
            lines = section.strip().split('\n')
            if not lines:
                continue
                
            place_name = lines[0].strip()
            description = '\n'.join(lines[1:]).strip()
            
            if not description:
                continue
                
            doc = {
                "text": f"{place_name}: {description}",
                "meta": {
                    "category": "Gastronomy",
                    "topic": place_name,
                    "type": "dining",
                    "keywords": self._extract_keywords(f"{place_name} {description}", "gastronomy")
                }
            }
            
            # Add location if found
            location_info = self._get_location_info(place_name)
            if location_info:
                doc["meta"]["location"] = location_info
                
            documents.append(doc)
            
        return documents
        
    def process_timetable_file(self, filepath: Path) -> List[Dict[str, Any]]:
        """Process timetable file."""
        documents = []
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        current_day = None
        current_event = {}
        
        for line in content.split('\n'):
            line = line.strip()
            
            # Check for day headers (### Wednesday, July 30th)
            if line.startswith('### ') and ('day' in line.lower() or 'july' in line.lower() or 'august' in line.lower()):
                current_day = line.replace('###', '').strip()
                continue
                
            # Check for artist/event name (## Artist Name)
            if line.startswith('## '):
                # Save previous event if exists
                if current_event and 'name' in current_event:
                    doc = self._create_timetable_doc(current_event, current_day)
                    if doc:
                        documents.append(doc)
                        
                # Start new event
                current_event = {'name': line.replace('##', '').strip()}
                
            # Parse event details
            elif line.startswith('**Stage:**'):
                current_event['stage'] = line.replace('**Stage:**', '').strip()
            elif line.startswith('**Time:**'):
                current_event['time'] = line.replace('**Time:**', '').strip()
            elif line.startswith('**Type:**'):
                current_event['type'] = line.replace('**Type:**', '').strip()
                
        # Don't forget the last event
        if current_event and 'name' in current_event:
            doc = self._create_timetable_doc(current_event, current_day)
            if doc:
                documents.append(doc)
                
        return documents
        
    def _create_timetable_doc(self, event: Dict[str, str], day: str) -> Optional[Dict[str, Any]]:
        """Create a document from timetable event data."""
        if not all(k in event for k in ['name', 'stage', 'time']):
            return None
            
        event_type = event.get('type', 'DJ').upper() if event.get('type') else 'DJ'
        
        doc = {
            "text": f"{event['name']} performs at {event['stage']} on {day} at {event['time']}",
            "meta": {
                "category": "Timetable",
                "topic": f"{event['name']} @ {event['stage']}",
                "type": event_type,
                "event": {
                    "name": event['name'],
                    "day": day,
                    "time": event['time']
                },
                "keywords": self._extract_keywords(f"{event['name']} {event['stage']} {day}", "timetable")
            }
        }
        
        # Add location for stage
        location_info = self._get_location_info(event['stage'])
        if location_info:
            doc["meta"]["location"] = location_info
            
        return doc
        
    def process_workshops_file(self, filepath: Path) -> List[Dict[str, Any]]:
        """Process workshops file."""
        documents = []
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Split by ### headers (workshops)
        sections = re.split(r'^###\s+', content, flags=re.MULTILINE)[1:]
        
        for section in sections:
            lines = section.strip().split('\n')
            if not lines:
                continue
                
            workshop_title = lines[0].strip()
            details = '\n'.join(lines[1:]).strip()
            
            # Extract facilitator if present
            facilitator_match = re.search(r'Facilitator:\s*(.*?)(?:\n|$)', details)
            facilitator = facilitator_match.group(1).strip() if facilitator_match else None
            
            # Extract time/day if present
            time_match = re.search(r'When:\s*(.*?)(?:\n|$)', details)
            when = time_match.group(1).strip() if time_match else None
            
            doc = {
                "text": f"{workshop_title}\n{details}",
                "meta": {
                    "category": "Workshops",
                    "topic": workshop_title,
                    "type": "workshop",
                    "keywords": self._extract_keywords(f"{workshop_title} {details}", "workshops")
                }
            }
            
            # Add event details if available
            event_info = {"name": workshop_title}
            if facilitator:
                event_info["facilitator"] = facilitator
            if when:
                # Try to parse day and time
                day_time_match = re.match(r'(.*?)\s+at\s+([\d:]+)', when)
                if day_time_match:
                    event_info["day"] = day_time_match.group(1)
                    event_info["time"] = day_time_match.group(2)
                    
            if len(event_info) > 1:
                doc["meta"]["event"] = event_info
                
            # Add location if mentioned
            location_info = self._get_location_info(details)
            if location_info:
                doc["meta"]["location"] = location_info
                
            documents.append(doc)
            
        return documents
        
    def process_general_files(self, filepath: Path) -> List[Dict[str, Any]]:
        """Process general information files."""
        documents = []
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Split by ## or ### headers
        sections = re.split(r'^##(?:#?)\s+', content, flags=re.MULTILINE)[1:]
        
        for section in sections:
            lines = section.strip().split('\n')
            if not lines:
                continue
                
            topic = lines[0].strip()
            text = '\n'.join(lines[1:]).strip()
            
            if not text:
                continue
                
            # Determine category based on content
            category = "General"
            if "sustainability" in topic.lower() or "eco" in topic.lower():
                category = "Sustainability"
            elif "travel" in topic.lower() or "transport" in topic.lower():
                category = "Travel"
            elif "safety" in topic.lower() or "security" in topic.lower():
                category = "Safety"
                
            doc = {
                "text": f"{topic}\n{text}",
                "meta": {
                    "category": category,
                    "topic": topic,
                    "type": "general info",
                    "keywords": self._extract_keywords(f"{topic} {text}", "general")
                }
            }
            
            # Add location if mentioned
            location_info = self._get_location_info(text)
            if location_info:
                doc["meta"]["location"] = location_info
                
            documents.append(doc)
            
        return documents
        
    def process_all_files(self) -> None:
        """Process all markdown files and combine results."""
        file_processors = {
            "garbicz_faq_chunked(en).md": self.process_faq_file,
            "garbicz_gastro_highlights.md": self.process_gastro_file,
            "garbicz_timetable_chunked(en).md": self.process_timetable_file,
            "garbicz_workshops.md": self.process_workshops_file,
            "garbicz-general.md": self.process_general_files,
            "garbicz-overview.md": self.process_general_files
        }
        
        for filename, processor in file_processors.items():
            filepath = Path(filename)
            if filepath.exists():
                print(f"Processing {filename}...")
                try:
                    docs = processor(filepath)
                    self.processed_data.extend(docs)
                    print(f"  - Extracted {len(docs)} documents")
                except Exception as e:
                    print(f"  - Error processing {filename}: {e}")
            else:
                print(f"Warning: {filename} not found")
                
    def save_to_json(self, output_file: str = "garbicz_data.json") -> None:
        """Save processed data to JSON file."""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.processed_data, f, indent=2, ensure_ascii=False)
        print(f"\nSaved {len(self.processed_data)} documents to {output_file}")


def main():
    processor = GarbiczDataProcessor()
    processor.process_all_files()
    processor.save_to_json()
    print("\nData processing complete!")


if __name__ == "__main__":
    main()