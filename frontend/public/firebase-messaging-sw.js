/* eslint-disable no-undef */
// Service worker for Firebase Cloud Messaging background web push notifications

const params = new URLSearchParams(self.location.search);
const firebaseConfig = {
  apiKey: params.get('apiKey'),
  projectId: params.get('projectId'),
  messagingSenderId: params.get('messagingSenderId'),
  appId: params.get('appId'),
};

if (
  firebaseConfig.apiKey &&
  firebaseConfig.projectId &&
  firebaseConfig.messagingSenderId &&
  firebaseConfig.appId
) {
  importScripts('https://www.gstatic.com/firebasejs/12.17.1/firebase-app-compat.js');
  importScripts('https://www.gstatic.com/firebasejs/12.17.1/firebase-messaging-compat.js');

  try {
    firebase.initializeApp(firebaseConfig);
    const messaging = firebase.messaging();

    messaging.onBackgroundMessage((payload) => {
      const notificationTitle =
        payload.notification?.title || payload.data?.title || 'NextGig Notification';
      const notificationOptions = {
        body:
          payload.notification?.body ||
          payload.data?.body ||
          payload.data?.message ||
          '',
        icon: '/favicon.ico',
        data: payload.data || {},
      };

      return self.registration.showNotification(notificationTitle, notificationOptions);
    });
  } catch (err) {
    console.error('[firebase-messaging-sw] Failed to initialize FCM in service worker:', err);
  }
}

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const targetUrl = event.notification.data?.url || '/dashboard';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if ('focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(targetUrl);
      }
    })
  );
});
