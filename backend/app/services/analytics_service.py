"""Analytics service – overview stats and CBIR evaluation metrics."""

from app.models.image import Image
from app.models.category import Category
from app.models.search import SearchSession, FeedbackIteration, SearchHistory


class AnalyticsService:
    @staticmethod
    def get_overview(user_id):
        total_images = Image.query.count()
        total_categories = Category.query.count()
        user_uploads = Image.query.filter_by(source_type='upload').count()
        total_searches = SearchHistory.query.filter_by(user_id=user_id).count()
        indexed_count = Image.query.filter_by(is_indexed=True).count()

        # Category distribution
        categories = Category.query.all()
        category_distribution = []
        for cat in categories:
            count = Image.query.filter_by(category_id=cat.id).count()
            if count > 0:
                category_distribution.append({
                    'category_id': cat.id,
                    'category_name': cat.name,
                    'image_count': count,
                })
        category_distribution.sort(key=lambda x: x['image_count'], reverse=True)

        # Recent activity (last 10 searches)
        recent = SearchHistory.query.filter_by(user_id=user_id).order_by(SearchHistory.created_at.desc()).limit(10).all()
        recent_activity = [h.to_dict() for h in recent]

        return {
            'total_images': total_images,
            'categories': total_categories,
            'user_uploads': user_uploads,
            'searches': total_searches,
            'index_status': {
                'total': total_images,
                'indexed': indexed_count,
            },
            'category_distribution': category_distribution,
            'recent_activity': recent_activity,
        }

    @staticmethod
    def get_evaluation(user_id):
        """Return aggregate CBIR precision/recall metrics from feedback iterations."""
        iterations = FeedbackIteration.query.join(SearchSession).filter(
            SearchSession.user_id == user_id,
            FeedbackIteration.precision_at_k.isnot(None)
        ).order_by(FeedbackIteration.id).all()

        if not iterations:
            return {
                'total_evaluated_sessions': 0,
                'avg_precision_at_k': None,
                'avg_recall_at_k': None,
                'iterations': [],
            }

        precisions = [it.precision_at_k for it in iterations if it.precision_at_k is not None]
        recalls = [it.recall_at_k for it in iterations if it.recall_at_k is not None]

        return {
            'total_evaluated_sessions': len(set(it.session_id for it in iterations)),
            'avg_precision_at_k': sum(precisions) / len(precisions) if precisions else None,
            'avg_recall_at_k': sum(recalls) / len(recalls) if recalls else None,
            'total_iterations': len(iterations),
            'iterations': [it.to_dict() for it in iterations[-20:]],  # last 20
        }
