#!/usr/bin/env python3
"""
Real-time parsing performance monitor.
This script monitors the parsing comparison logs and provides live insights
about where LLM performs better than regex parsing.
"""

import json
import time
import os
from datetime import datetime
from pathlib import Path
from src.training.comparison_logger import ParseComparisonAnalyzer

class RealTimeMonitor:
    """Real-time monitor for parsing comparisons"""
    
    def __init__(self, log_file="parsing_comparisons.log", update_interval=5):
        self.log_file = log_file
        self.update_interval = update_interval
        self.analyzer = ParseComparisonAnalyzer(log_file)
        self.last_position = 0
        
    def get_file_size(self):
        """Get current log file size"""
        try:
            return os.path.getsize(self.log_file)
        except FileNotFoundError:
            return 0
    
    def has_new_data(self):
        """Check if log file has new data"""
        current_size = self.get_file_size()
        if current_size > self.last_position:
            self.last_position = current_size
            return True
        return False
    
    def get_recent_stats(self):
        """Get statistics from recent comparisons"""
        try:
            # Get comparisons from last hour
            comparisons = self.analyzer.load_comparisons(days_back=1)
            
            if not comparisons:
                return {"no_data": True}
            
            # Filter to last hour
            one_hour_ago = datetime.now().timestamp() - 3600
            recent_comparisons = [
                comp for comp in comparisons
                if datetime.fromisoformat(comp['timestamp']).timestamp() > one_hour_ago
            ]
            
            if not recent_comparisons:
                return {"no_recent_data": True, "total_comparisons": len(comparisons)}
            
            # Calculate stats
            total_recent = len(recent_comparisons)
            llm_better_count = sum(1 for comp in recent_comparisons if comp.get('llm_better', False))
            
            intent_differences = sum(
                1 for comp in recent_comparisons 
                if comp['regex_result']['intent'] != comp['llm_result']['intent']
            )
            
            avg_regex_conf = sum(
                comp['regex_result']['confidence'] 
                for comp in recent_comparisons
            ) / total_recent
            
            avg_llm_conf = sum(
                comp['llm_result']['confidence'] 
                for comp in recent_comparisons
            ) / total_recent
            
            return {
                "total_recent": total_recent,
                "llm_better_count": llm_better_count,
                "llm_better_rate": (llm_better_count / total_recent) * 100,
                "intent_differences": intent_differences,
                "intent_diff_rate": (intent_differences / total_recent) * 100,
                "avg_regex_confidence": avg_regex_conf,
                "avg_llm_confidence": avg_llm_conf,
                "confidence_gap": avg_llm_conf - avg_regex_conf
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def display_stats(self, stats):
        """Display statistics in a formatted way"""
        os.system('clear' if os.name == 'posix' else 'cls')  # Clear screen
        
        print("🔍 Real-Time Parsing Performance Monitor")
        print("=" * 50)
        print(f"Monitoring: {self.log_file}")
        print(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
        print()
        
        if stats.get("no_data"):
            print("📊 Status: No comparison data found")
            print("   Run some queries to generate comparison data!")
            return
            
        if stats.get("no_recent_data"):
            print(f"📊 Status: No recent data (last hour)")
            print(f"   Total comparisons in log: {stats.get('total_comparisons', 0)}")
            print("   Waiting for new queries...")
            return
            
        if stats.get("error"):
            print(f"❌ Error: {stats['error']}")
            return
        
        # Display main metrics
        print("📊 Last Hour Statistics:")
        print("-" * 25)
        print(f"Total Comparisons: {stats['total_recent']}")
        print(f"LLM Better Cases: {stats['llm_better_count']} ({stats['llm_better_rate']:.1f}%)")
        print(f"Intent Differences: {stats['intent_differences']} ({stats['intent_diff_rate']:.1f}%)")
        print()
        
        # Confidence comparison
        print("🎯 Confidence Analysis:")
        print("-" * 22)
        print(f"Avg Regex Confidence: {stats['avg_regex_confidence']:.3f}")
        print(f"Avg LLM Confidence:   {stats['avg_llm_confidence']:.3f}")
        print(f"Confidence Gap:       {stats['confidence_gap']:+.3f}")
        print()
        
        # Performance indicators
        print("🚦 Performance Indicators:")
        print("-" * 26)
        
        # LLM advantage rate
        llm_rate = stats['llm_better_rate']
        if llm_rate > 30:
            print(f"🟢 LLM Advantage: HIGH ({llm_rate:.1f}%) - Consider switching to LLM")
        elif llm_rate > 15:
            print(f"🟡 LLM Advantage: MEDIUM ({llm_rate:.1f}%) - Monitor closely")
        else:
            print(f"🔴 LLM Advantage: LOW ({llm_rate:.1f}%) - Regex performing well")
        
        # Intent accuracy
        intent_diff_rate = stats['intent_diff_rate']
        if intent_diff_rate > 25:
            print(f"🟠 Intent Differences: HIGH ({intent_diff_rate:.1f}%) - Check patterns")
        elif intent_diff_rate > 10:
            print(f"🟡 Intent Differences: MEDIUM ({intent_diff_rate:.1f}%) - Normal variation")
        else:
            print(f"🟢 Intent Differences: LOW ({intent_diff_rate:.1f}%) - Good agreement")
        
        # Confidence analysis
        conf_gap = stats['confidence_gap']
        if conf_gap > 0.1:
            print(f"🟢 Confidence: LLM higher by {conf_gap:.3f}")
        elif conf_gap < -0.1:
            print(f"🔴 Confidence: Regex higher by {abs(conf_gap):.3f}")
        else:
            print(f"🟡 Confidence: Similar levels (gap: {conf_gap:+.3f})")
        
        print()
        print("💡 Recommendations:")
        print("-" * 16)
        
        # Generate real-time recommendations
        if llm_rate > 25:
            print("  • Consider enabling LLM mode for low-confidence regex queries")
        
        if intent_diff_rate > 20:
            print("  • Review regex patterns for intent detection")
            
        if stats['avg_regex_confidence'] < 0.6:
            print("  • Regex confidence low - LLM may provide better results")
            
        if stats['confidence_gap'] > 0.15:
            print("  • LLM consistently more confident - validate with real data")
        
        print()
        print("Press Ctrl+C to stop monitoring...")
    
    def run(self):
        """Run the real-time monitor"""
        print("🚀 Starting Real-Time Parsing Monitor...")
        print(f"Monitoring file: {self.log_file}")
        print(f"Update interval: {self.update_interval}s")
        print()
        
        try:
            while True:
                stats = self.get_recent_stats()
                self.display_stats(stats)
                time.sleep(self.update_interval)
                
        except KeyboardInterrupt:
            print("\n⏹️  Monitor stopped by user")
        except Exception as e:
            print(f"\n❌ Monitor error: {e}")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Real-time parsing performance monitor")
    parser.add_argument("--log-file", default="parsing_comparisons.log", 
                       help="Path to comparison log file")
    parser.add_argument("--interval", type=int, default=5,
                       help="Update interval in seconds")
    
    args = parser.parse_args()
    
    monitor = RealTimeMonitor(
        log_file=args.log_file,
        update_interval=args.interval
    )
    
    monitor.run()

if __name__ == "__main__":
    main()