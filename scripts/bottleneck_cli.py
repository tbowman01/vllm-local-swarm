#!/usr/bin/env python3
"""
vLLM Local Swarm Bottleneck Detection CLI
========================================

Command-line interface that mimics the claude-flow bottleneck detect command
with comprehensive performance analysis and automatic optimization capabilities.

Usage:
    python scripts/bottleneck_cli.py [options]
    python scripts/bottleneck_cli.py --time-range 24h --fix --threshold 15
"""

import asyncio
import argparse
import json
import logging
import sys
import os
from typing import Dict, List, Any

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

from scripts.bottleneck_detector import BottleneckDetector, BottleneckSeverity
from scripts.performance_optimizer import PerformanceOptimizer, OptimizationLevel
from scripts.performance_hooks import PerformanceHookManager

logger = logging.getLogger(__name__)


class BottleneckCLI:
    """
    Command-line interface for bottleneck detection and performance optimization
    """
    
    def __init__(self):
        self.detector = None
        self.optimizer = None
        self.hook_manager = None
        
    def create_parser(self) -> argparse.ArgumentParser:
        """Create command line argument parser"""
        parser = argparse.ArgumentParser(
            description="vLLM Local Swarm Bottleneck Detection and Optimization",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  Basic bottleneck detection:
    python scripts/bottleneck_cli.py
    
  Analyze specific time range:
    python scripts/bottleneck_cli.py --time-range 24h
    
  Export analysis results:
    python scripts/bottleneck_cli.py --export bottlenecks.json
    
  Auto-fix detected issues:
    python scripts/bottleneck_cli.py --fix --threshold 15
    
  Conservative optimization:
    python scripts/bottleneck_cli.py --fix --optimization-level conservative
    
  Complete analysis with export:
    python scripts/bottleneck_cli.py -t 24h -e analysis.json --fix --threshold 20
            """
        )
        
        parser.add_argument(
            '--time-range', '-t',
            default='1h',
            choices=['1h', '24h', '7d', 'all'],
            help='Analysis period (default: 1h)'
        )
        
        parser.add_argument(
            '--threshold',
            type=float,
            default=20.0,
            help='Bottleneck threshold percentage (default: 20.0)'
        )
        
        parser.add_argument(
            '--export', '-e',
            help='Export analysis to file'
        )
        
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Apply automatic optimizations'
        )
        
        parser.add_argument(
            '--optimization-level',
            choices=['conservative', 'moderate', 'aggressive'],
            default='moderate',
            help='Optimization aggressiveness (default: moderate)'
        )
        
        parser.add_argument(
            '--redis-url',
            default='redis://localhost:6379',
            help='Redis connection URL (default: redis://localhost:6379)'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what optimizations would be applied without executing them'
        )
        
        parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Enable verbose output'
        )
        
        parser.add_argument(
            '--monitor',
            action='store_true',
            help='Start continuous monitoring mode'
        )
        
        parser.add_argument(
            '--monitor-interval',
            type=int,
            default=60,
            help='Monitoring interval in seconds (default: 60)'
        )
        
        return parser
    
    async def run(self, args):
        """Run the bottleneck detection CLI"""
        
        # Configure logging
        log_level = logging.DEBUG if args.verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        try:
            # Initialize components
            await self._initialize_components(args)
            
            if args.monitor:
                await self._run_continuous_monitoring(args)
            else:
                await self._run_single_analysis(args)
                
        except KeyboardInterrupt:
            logger.info("⏹️ Analysis interrupted by user")
        except Exception as e:
            logger.error(f"❌ CLI execution failed: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)
    
    async def _initialize_components(self, args):
        """Initialize detection and optimization components"""
        logger.info("🚀 Initializing vLLM Local Swarm Bottleneck Detection...")
        
        # Initialize bottleneck detector
        self.detector = BottleneckDetector(
            redis_url=args.redis_url,
            time_range=args.time_range,
            threshold=args.threshold
        )
        
        # Initialize optimizer if fixing is enabled
        if args.fix or args.dry_run:
            optimization_level = OptimizationLevel(args.optimization_level)
            self.optimizer = PerformanceOptimizer(
                redis_url=args.redis_url,
                optimization_level=optimization_level
            )
        
        # Initialize performance hooks
        self.hook_manager = PerformanceHookManager(redis_url=args.redis_url)
        
        logger.info("✅ Components initialized successfully")
    
    async def _run_single_analysis(self, args):
        """Run a single bottleneck analysis"""
        print(f"""
🔍 Bottleneck Analysis Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Configuration:
├── Time Range: {args.time_range}
├── Threshold: {args.threshold}%
├── Optimization: {'Enabled' if args.fix else 'Disabled'}
└── Level: {args.optimization_level if args.fix else 'N/A'}
""")
        
        # Perform bottleneck analysis
        logger.info("🔍 Starting bottleneck analysis...")
        report = await self.detector.analyze(
            export_file=args.export,
            apply_fixes=False  # We'll handle fixes separately
        )
        
        # Display analysis results
        self._display_analysis_results(report)
        
        # Apply optimizations if requested
        if args.fix or args.dry_run:
            await self._handle_optimizations(args, report)
        
        # Display final summary
        self._display_final_summary(args, report)
    
    async def _run_continuous_monitoring(self, args):
        """Run continuous monitoring mode"""
        logger.info(f"📊 Starting continuous monitoring (interval: {args.monitor_interval}s)")
        
        print(f"""
🔄 Continuous Monitoring Mode
━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Configuration:
├── Interval: {args.monitor_interval}s
├── Threshold: {args.threshold}%
├── Auto-fix: {'Enabled' if args.fix else 'Disabled'}
└── Level: {args.optimization_level if args.fix else 'N/A'}

Press Ctrl+C to stop monitoring...
""")
        
        iteration = 0
        try:
            while True:
                iteration += 1
                print(f"\n🔄 Monitoring Iteration #{iteration} - {args.time_range}")
                
                # Run analysis
                report = await self.detector.analyze()
                
                # Quick summary
                critical_count = len(report.critical_issues)
                warning_count = len(report.warning_issues)
                
                if critical_count > 0:
                    print(f"🚨 {critical_count} critical issues detected")
                    
                    # Auto-fix if enabled
                    if args.fix:
                        await self._handle_optimizations(args, report, quiet=True)
                else:
                    print(f"✅ System healthy ({warning_count} warnings)")
                
                # Wait for next iteration
                await asyncio.sleep(args.monitor_interval)
                
        except KeyboardInterrupt:
            logger.info("🛑 Continuous monitoring stopped")
    
    def _display_analysis_results(self, report):
        """Display bottleneck analysis results"""
        
        print(f"""
📊 Analysis Summary
├── Agents Analyzed: {report.agents_analyzed}
├── Tasks Processed: {report.tasks_processed}
├── Critical Issues: {len(report.critical_issues)}
├── Warning Issues: {len(report.warning_issues)}
└── Overall Health: {report.performance_summary.get('overall_health', 0):.1%}
""")
        
        # Display critical bottlenecks
        if report.critical_issues:
            print(f"\n🚨 Critical Bottlenecks")
            for i, issue in enumerate(report.critical_issues, 1):
                print(f"{i}. {issue.title} ({issue.impact_percentage:.0f}% impact)")
                print(f"   └── {issue.description}")
                if issue.affected_components:
                    print(f"   └── Affects: {', '.join(issue.affected_components)}")
        
        # Display warning bottlenecks
        if report.warning_issues:
            print(f"\n⚠️ Warning Bottlenecks")
            for i, issue in enumerate(report.warning_issues[:3], 1):  # Show top 3
                print(f"{i}. {issue.title} ({issue.impact_percentage:.0f}% impact)")
            
            if len(report.warning_issues) > 3:
                print(f"   └── ... and {len(report.warning_issues) - 3} more")
        
        # Display performance scores
        print(f"\n📈 Performance Scores")
        score_icons = {"🟢": lambda x: x > 0.8, "🟡": lambda x: x > 0.6, "🔴": lambda x: True}
        
        for category, score in report.performance_summary.items():
            if category == 'overall_health':
                continue
            icon = next(icon for icon, condition in score_icons.items() if condition(score))
            category_name = category.replace('_', ' ').title()
            print(f"{icon} {category_name}: {score:.1%}")
    
    async def _handle_optimizations(self, args, report, quiet=False):
        """Handle optimization application"""
        
        # Convert report issues to optimizer format
        bottleneck_issues = []
        for issue in report.critical_issues + report.warning_issues:
            bottleneck_issues.append({
                'category': issue.category.value,
                'severity': issue.severity.value,
                'title': issue.title,
                'impact_percentage': issue.impact_percentage
            })
        
        if not bottleneck_issues:
            if not quiet:
                print(f"\n✅ No optimizations needed - system is performing well!")
            return
        
        if not quiet:
            print(f"\n🔧 Optimization Analysis")
            print(f"{'='*50}")
        
        # Run optimizer
        optimization_result = await self.optimizer.optimize_system(
            bottleneck_issues=bottleneck_issues,
            dry_run=args.dry_run
        )
        
        if optimization_result['status'] == 'success':
            applied_count = optimization_result.get('optimizations_applied', 0)
            expected_improvement = optimization_result.get('total_expected_improvement', 0)
            
            if args.dry_run:
                if not quiet:
                    print(f"🔍 [DRY RUN] Would apply {applied_count} optimizations")
                    print(f"📈 Expected improvement: {expected_improvement:.1f}%")
            else:
                if not quiet:
                    print(f"✅ Applied {applied_count} optimizations")
                    print(f"📈 Expected improvement: {expected_improvement:.1f}%")
                
                if optimization_result.get('requires_restart', False):
                    print(f"🔄 Some optimizations require service restart")
                    print(f"   Run: docker-compose restart")
        
        elif optimization_result['status'] == 'no_optimizations':
            if not quiet:
                print(f"ℹ️ {optimization_result.get('message', 'No optimizations available')}")
        
        else:
            if not quiet:
                print(f"❌ Optimization failed: {optimization_result.get('error', 'Unknown error')}")
        
        # Display optimization details
        if not quiet and optimization_result.get('results'):
            print(f"\n🔧 Optimization Details:")
            for result in optimization_result['results']:
                status_icon = "✅" if result.get('status') == 'success' else "❌"
                optimization_name = result.get('optimization', 'Unknown')
                print(f"{status_icon} {optimization_name}")
                
                if result.get('expected_improvement'):
                    print(f"   └── Expected improvement: {result['expected_improvement']}")
    
    def _display_final_summary(self, args, report):
        """Display final summary"""
        
        print(f"\n💡 Recommendations")
        print(f"{'='*50}")
        
        # Collect unique recommendations
        all_recommendations = set()
        for issue in report.critical_issues + report.warning_issues:
            all_recommendations.update(issue.recommendations)
        
        if all_recommendations:
            for i, rec in enumerate(list(all_recommendations)[:5], 1):
                print(f"{i}. {rec}")
        else:
            print("✅ No specific recommendations - system is optimized")
        
        # Show quick fixes if available
        if report.auto_fixes_available:
            print(f"\n✅ Quick Fixes Available:")
            print("Run with --fix to apply:")
            for fix in report.auto_fixes_available[:3]:
                print(f"• {fix}")
        
        # Show export info
        if args.export:
            print(f"\n📊 Full analysis exported to: {args.export}")
        
        # Show optimization potential
        total_potential = sum(report.optimization_potential.values())
        if total_potential > 0:
            print(f"\n📈 Optimization Potential: {total_potential:.0%} improvement available")
        
        print(f"\n🎯 Analysis Complete")
        
        # Final recommendations based on findings
        if len(report.critical_issues) > 0:
            print("🚨 Action Required: Address critical bottlenecks immediately")
        elif len(report.warning_issues) > 2:
            print("⚠️ Consider running optimizations to improve performance")
        else:
            print("✅ System performing well - monitor regularly")


async def main():
    """Main function"""
    cli = BottleneckCLI()
    parser = cli.create_parser()
    args = parser.parse_args()
    
    await cli.run(args)


if __name__ == "__main__":
    asyncio.run(main())