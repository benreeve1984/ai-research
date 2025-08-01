"""Paper ranking and selection logic."""

import logging
import math
from typing import List
from .harvest import Paper


logger = logging.getLogger(__name__)


def normalize_github_stars(papers: List[Paper]) -> List[Paper]:
    """Normalize GitHub stars using min-max scaling."""
    if not papers:
        return papers
    
    # Get all star counts
    star_counts = [p.github_stars or 0 for p in papers]
    
    if not star_counts or max(star_counts) == min(star_counts):
        # All papers have same stars (or all zero), set normalized to 0
        for paper in papers:
            paper._normalized_stars = 0.0
        return papers
    
    max_stars = max(star_counts)
    min_stars = min(star_counts)
    
    for paper in papers:
        stars = paper.github_stars or 0
        normalized = (stars - min_stars) / (max_stars - min_stars)
        paper._normalized_stars = normalized
    
    return papers


def calculate_paper_score(paper: Paper, 
                         citation_weight: float = 0.5,
                         github_weight: float = 0.3,
                         social_weight: float = 0.2) -> float:
    """Calculate ranking score for a paper."""
    
    # Citation component (log-scaled)
    citations = paper.citation_count or 0
    citation_score = math.log(citations + 1)
    
    # GitHub component (normalized)
    github_score = getattr(paper, '_normalized_stars', 0.0)
    
    # Social buzz component (placeholder for future implementation)
    social_score = 0.0
    
    # Weighted combination
    total_score = (citation_weight * citation_score + 
                  github_weight * github_score + 
                  social_weight * social_score)
    
    return total_score


def rank_papers(papers: List[Paper],
               top_k: int = 10,
               citation_weight: float = 0.5,
               github_weight: float = 0.3, 
               social_weight: float = 0.2) -> List[Paper]:
    """Rank papers and return top K."""
    
    if not papers:
        logger.warning("No papers to rank")
        return []
    
    logger.info(f"Ranking {len(papers)} papers")
    
    # Normalize GitHub stars across all papers
    papers = normalize_github_stars(papers)
    
    # Calculate scores for all papers
    for paper in papers:
        score = calculate_paper_score(
            paper, 
            citation_weight=citation_weight,
            github_weight=github_weight,
            social_weight=social_weight
        )
        paper.score = score
        
        logger.debug(
            f"Paper: {paper.title[:50]}... | "
            f"Citations: {paper.citation_count} | "
            f"Stars: {paper.github_stars} | "
            f"Score: {score:.3f}"
        )
    
    # Sort by score (descending) and take top K
    ranked_papers = sorted(papers, key=lambda p: p.score or 0, reverse=True)
    top_papers = ranked_papers[:top_k]
    
    logger.info(f"Selected top {len(top_papers)} papers")
    
    # Log top papers
    for i, paper in enumerate(top_papers, 1):
        logger.info(
            f"#{i}: {paper.title} "
            f"(Score: {paper.score:.3f}, Citations: {paper.citation_count}, "
            f"Stars: {paper.github_stars})"
        )
    
    return top_papers