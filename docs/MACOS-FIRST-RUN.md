# Opening GLF Assessment Scheduler on a Mac (first time only)

macOS shows a warning the first time because the app is not from the App Store. It is safe; you only do this once.

1. Unzip the download and double-click **GLF Assessment Scheduler**. A Terminal window may open.
2. macOS says it cannot verify the app. Click **Done** (or **OK**).
3. Open **System Settings → Privacy & Security**.
4. Scroll down to the message *"GLF Assessment Scheduler was blocked"* and click **Open Anyway**.
5. Enter your Mac password, then click **Open Anyway** again.
6. The scheduler opens in your web browser. Next time, just double-click it.

On older macOS versions you can instead right-click the app, choose **Open**, then **Open** again.

Keep the Terminal window open while using the scheduler; close it to stop the app.

If you still see "is damaged and can't be opened", the file was marked as downloaded. Ask IT to run `xattr -cr "GLF Assessment Scheduler"` once.
