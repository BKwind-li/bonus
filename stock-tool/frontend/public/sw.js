self.addEventListener("push", (event) => {
  const data = event.data?.json() ?? {}
  event.waitUntil(
    self.registration.showNotification(data.title || "投资助手提醒", {
      body: data.body || "",
      icon: "/favicon.ico",
      badge: "/favicon.ico",
    })
  )
})

self.addEventListener("notificationclick", (event) => {
  event.notification.close()
  event.waitUntil(clients.openWindow("/alerts"))
})
