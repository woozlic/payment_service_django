import logging
import random
import time

from celery import shared_task
from django.db import transaction

from .models import Payout

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def process_payout(self, id) -> str:
    time.sleep(random.uniform(2,5))

    with transaction.atomic():
        payout = (Payout.objects
                  .select_for_update()
                  .filter(id=id, status=Payout.Status.PENDING)
                  .first())
        if payout is None:
            logger.info(f'payout {id} is not pending, skip')
            return 'skipped'

        payout.status = (Payout.Status.PAID if random.random() < 0.8
                         else Payout.Status.FAILED)
        payout.save(update_fields=['status', 'updated_at'])

    logger.info(f'payout {id} -> {payout.status}')
    return payout.status

@shared_task
def process_pending_payouts(limit: int = 100) -> int:
    from .models import Payout

    ids = list(
        Payout.objects
        .filter(status=Payout.Status.PENDING, is_deleted=False)
        .order_by("created_at")
        .values_list("id", flat=True)[:limit]
    )
    for u in ids:
        process_payout.delay(str(u))
    return len(ids)