#define _GNU_SOURCE
#include <dlfcn.h>
#include <string.h>
#include <gtk/gtk.h>

static void
settle (void)
{
  gint64 deadline = g_get_monotonic_time () + 150 * G_TIME_SPAN_MILLISECOND;
  while (g_get_monotonic_time () < deadline)
    {
      while (g_main_context_iteration (NULL, FALSE)) {}
      g_usleep (1000);
    }
}

static void
snapshot_window (GtkWidget *window)
{
  GdkPaintable *paintable = gtk_widget_paintable_new (window);
  GtkSnapshot *snapshot = gtk_snapshot_new ();
  GskRenderNode *node;

  gdk_paintable_snapshot (paintable, GDK_SNAPSHOT (snapshot),
                          gtk_widget_get_width (window), gtk_widget_get_height (window));
  node = gtk_snapshot_free_to_node (snapshot);
  g_assert_nonnull (node);
  gsk_render_node_unref (node);
  g_object_unref (paintable);
}

int
main (void)
{
  GtkWidget *window, *scroller, *child;
  GtkAdjustment *horizontal, *vertical;
  GString *text;

  Dl_info loaded;
  const char *expected = g_getenv ("GTK_BOUNCE_EXPECT_PATH");
  g_assert_nonnull (expected);
  g_assert_cmpint (dladdr ((void *) gtk_get_major_version, &loaded), !=, 0);
  g_assert_nonnull (strstr (loaded.dli_fname, expected));
  g_assert_cmpuint (gtk_get_minor_version (), ==, 22);
  g_assert_cmpuint (gtk_get_micro_version (), ==, 5);
  g_print ("PASS: loaded patched GTK from %s\n", loaded.dli_fname);
  gtk_init ();
  window = gtk_window_new ();
  gtk_window_set_default_size (GTK_WINDOW (window), 400, 300);
  scroller = gtk_scrolled_window_new ();
  gtk_scrolled_window_set_policy (GTK_SCROLLED_WINDOW (scroller),
                                  GTK_POLICY_ALWAYS, GTK_POLICY_ALWAYS);
  gtk_scrolled_window_set_overlay_scrolling (GTK_SCROLLED_WINDOW (scroller), FALSE);
  child = gtk_text_view_new ();
  text = g_string_new (NULL);
  for (int line = 0; line < 200; line++)
    g_string_append_printf (text, "Line %d: GTK 4 bounce scrolling rendering test with a long unwrapped line extending beyond the viewport.\n", line);
  gtk_text_buffer_set_text (gtk_text_view_get_buffer (GTK_TEXT_VIEW (child)),
                            text->str, -1);
  g_string_free (text, TRUE);
  gtk_scrolled_window_set_child (GTK_SCROLLED_WINDOW (scroller), child);
  gtk_window_set_child (GTK_WINDOW (window), scroller);
  gtk_window_present (GTK_WINDOW (window));
  settle ();
  horizontal = gtk_scrolled_window_get_hadjustment (GTK_SCROLLED_WINDOW (scroller));
  vertical = gtk_scrolled_window_get_vadjustment (GTK_SCROLLED_WINDOW (scroller));
  g_assert_cmpfloat (gtk_adjustment_get_upper (horizontal), >,
                    gtk_adjustment_get_page_size (horizontal));
  g_assert_cmpfloat (gtk_adjustment_get_upper (vertical), >,
                    gtk_adjustment_get_page_size (vertical));

  for (int position = 0; position < 3; position++)
    {
      double fraction = position / 2.0;
      gtk_adjustment_set_value (horizontal, fraction *
        (gtk_adjustment_get_upper (horizontal) - gtk_adjustment_get_page_size (horizontal)));
      gtk_adjustment_set_value (vertical, fraction *
        (gtk_adjustment_get_upper (vertical) - gtk_adjustment_get_page_size (vertical)));
      settle ();
      snapshot_window (window);
    }

  gtk_scrolled_window_set_child (GTK_SCROLLED_WINDOW (scroller), NULL);
  settle ();
  snapshot_window (window);
  gtk_window_destroy (GTK_WINDOW (window));
  settle ();
  g_print ("PASS: installed GTK renders both scrollbars, scroll boundaries, and an empty child.\n");
  return 0;
}
