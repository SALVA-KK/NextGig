import logging
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import Application, Opportunity

from django.db import transaction
from apps.notifications.models import Notification
from apps.notifications.services import create_notification

logger = logging.getLogger(__name__)


@shared_task
def notify_poster_of_new_application(application_id):
    """
    Celery task to send an email notification to the opportunity poster
    when a new application is submitted.
    """
    try:
        application = Application.objects.select_related(
            "opportunity", "opportunity__poster", "applicant"
        ).get(pk=application_id)

        poster = application.opportunity.poster
        applicant = application.applicant

        subject = f"New Application for '{application.opportunity.title}' on NextGig"
        message = (
            f"Hi {poster.full_name or poster.email},\n\n"
            f"{applicant.full_name or applicant.email} has applied for your opportunity "
            f"'{application.opportunity.title}'.\n\n"
            f"Cover Note: {application.cover_note or 'No cover note provided.'}\n\n"
            f"Log in to NextGig to review their application details.\n\n"
            f"Best regards,\nThe NextGig Team"
        )
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@nextgig.com")

        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[poster.email],
            fail_silently=False,
        )
        logger.info(f"Notification email sent to poster {poster.email} for application {application_id}.")
        return True
    except Application.DoesNotExist:
        logger.error(f"Application with ID {application_id} does not exist.")
        return False
    except Exception as e:
        logger.error(f"Failed to send application notification to poster: {e}")
        return False


@shared_task
def notify_applicant_of_status_change(application_id):
    """
    Celery task to send an email notification to the applicant
    when their application status is updated by the poster.
    """
    try:
        application = Application.objects.select_related(
            "opportunity", "applicant"
        ).get(pk=application_id)

        applicant = application.applicant
        status_display = application.get_status_display()

        subject = f"Application Status Update: '{application.opportunity.title}'"
        message = (
            f"Hi {applicant.full_name or applicant.email},\n\n"
            f"The status of your application for '{application.opportunity.title}' "
            f"has been updated to: {status_display}.\n\n"
            f"Log in to NextGig to view full details.\n\n"
            f"Best regards,\nThe NextGig Team"
        )
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@nextgig.com")

        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[applicant.email],
            fail_silently=False,
        )
        logger.info(f"Notification email sent to applicant {applicant.email} for application {application_id}.")
        return True
    except Application.DoesNotExist:
        logger.error(f"Application with ID {application_id} does not exist.")
        return False
    except Exception as e:
        logger.error(f"Failed to send status update notification to applicant: {e}")
        return False


@shared_task
def close_expired_opportunities():
    """
    Celery Beat periodic task to close opportunities whose deadline has passed.
    Handles each status transition and notification creation transactionally per opportunity.
    """
    today = timezone.now().date()
    expired_opps = list(
        Opportunity.objects.filter(
            status=Opportunity.Status.OPEN,
            deadline__lt=today,
        ).select_related("poster")
    )
    count = 0
    for opp in expired_opps:
        try:
            with transaction.atomic():
                opp.status = Opportunity.Status.CLOSED
                opp.close_reason = Opportunity.CloseReason.EXPIRED
                opp.closed_by = None
                opp.save(update_fields=["status", "close_reason", "closed_by", "updated_at"])
                create_notification(
                    recipient=opp.poster,
                    actor=None,
                    notification_type=Notification.NotificationType.OPPORTUNITY_EXPIRED,
                    title="Opportunity Expired",
                    message=f"Your opportunity '{opp.title}' has expired and was automatically closed.",
                    opportunity=opp,
                    event_key=f"opp_expire:{opp.id}",
                )
                count += 1
        except Exception as e:
            logger.error(f"Failed to close expired opportunity {opp.id}: {e}")

    logger.info(f"Celery Beat closed {count} expired opportunities on {today}.")
    return count
