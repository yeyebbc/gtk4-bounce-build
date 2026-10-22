/* Exercise bounce with native 32-bit and 64-bit clients of the packaged ABI. */
#include <gtk/gtk.h>
#include <math.h>
#include <string.h>

static void
settle (double seconds)
{
  gint64 deadline = g_get_monotonic_time () + (gint64)(seconds * G_USEC_PER_SEC);
  do
    {
      while (g_main_context_pending (NULL))
        g_main_context_iteration (NULL, FALSE);
      g_usleep (1000);
    }
  while (g_get_monotonic_time () < deadline);
}

static void
point (GtkWidget *widget, GtkWidget *window, gint *x, gint *y)
{
  g_assert_true (gtk_widget_translate_coordinates (widget, window, 0, 0, x, y));
}

static gboolean
draw_red (GtkWidget *widget, cairo_t *cr, gpointer data)
{
  (void)widget;
  (void)data;
  cairo_set_source_rgb (cr, 1, 0, 0);
  cairo_paint (cr);
  return FALSE;
}

static gboolean
red_pixel (cairo_surface_t *surface, gint x, gint y)
{
  guint32 pixel;
  cairo_surface_flush (surface);
  memcpy (&pixel, cairo_image_surface_get_data (surface) +
          y * cairo_image_surface_get_stride (surface) + x * 4, 4);
  return ((pixel >> 16) & 255) > 220 &&
         ((pixel >> 8) & 255) < 40 && (pixel & 255) < 40 &&
         ((pixel >> 24) & 255) > 220;
}

static GtkWidget *
make_child (gint kind)
{
  if (kind == 0)
    {
      GtkWidget *child = gtk_text_view_new ();
      GString *text = g_string_new ("");
      for (gint i = 0; i < 150; i++)
        {
          g_string_append_printf (text, "Line %d: ", i);
          for (gint j = 0; j < 15; j++)
            g_string_append (text, "long content ");
          g_string_append_c (text, '\n');
        }
      gtk_text_buffer_set_text (gtk_text_view_get_buffer (GTK_TEXT_VIEW (child)), text->str, -1);
      g_string_free (text, TRUE);
      return child;
    }
  if (kind == 1)
    {
      GtkListStore *store = gtk_list_store_new (1, G_TYPE_STRING);
      for (gint i = 0; i < 150; i++)
        {
          GtkTreeIter iter;
          gtk_list_store_append (store, &iter);
          gtk_list_store_set (store, &iter, 0,
                             "A long tree view row with content content content content content content content content content content content content content content", -1);
        }
      GtkWidget *child = gtk_tree_view_new_with_model (GTK_TREE_MODEL (store));
      gtk_tree_view_append_column (GTK_TREE_VIEW (child),
                                  gtk_tree_view_column_new_with_attributes ("Heading", gtk_cell_renderer_text_new (), "text", 0, NULL));
      g_object_unref (store);
      return child;
    }
  GtkWidget *child = gtk_drawing_area_new ();
  gtk_widget_set_size_request (child, 1400, 1400);
  g_signal_connect (child, "draw", G_CALLBACK (draw_red), NULL);
  return child;
}

int
main (int argc, char **argv)
{
  gboolean stock = argc == 2 && strcmp (argv[1], "--stock") == 0;
  gtk_init (NULL, NULL);
  GtkCssProvider *css = gtk_css_provider_new ();
  gtk_css_provider_load_from_data (css, "scrolledwindow, viewport { background-color: #ffffff; border: none; padding: 0; }", -1, NULL);
  gtk_style_context_add_provider_for_screen (gdk_screen_get_default (), GTK_STYLE_PROVIDER (css), GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);
  g_object_unref (css);
  gint count = 0;
  for (gint kind = 0; kind < 3; kind++)
    for (gint overlay = 0; overlay < 2; overlay++)
      {
        GtkWidget *window = gtk_window_new (GTK_WINDOW_TOPLEVEL);
        gtk_window_set_default_size (GTK_WINDOW (window), 420, 340);
        gtk_container_set_border_width (GTK_CONTAINER (window), 13);
        GtkWidget *scroller = gtk_scrolled_window_new (NULL, NULL);
        gtk_scrolled_window_set_policy (GTK_SCROLLED_WINDOW (scroller), GTK_POLICY_ALWAYS, GTK_POLICY_ALWAYS);
        gtk_scrolled_window_set_overlay_scrolling (GTK_SCROLLED_WINDOW (scroller), overlay);
        gtk_container_add (GTK_CONTAINER (window), scroller);
        gtk_container_add (GTK_CONTAINER (scroller), make_child (kind));
        gtk_widget_show_all (window);
        settle (.12);
        GtkWidget *child = gtk_bin_get_child (GTK_BIN (scroller));
        GtkWidget *bars[2] = {
          gtk_scrolled_window_get_hscrollbar (GTK_SCROLLED_WINDOW (scroller)),
          gtk_scrolled_window_get_vscrollbar (GTK_SCROLLED_WINDOW (scroller))
        };
        gint bx = 0, by = 0;
        for (gint edge_index = 0; edge_index < 4; edge_index++)
          {
            gboolean horizontal = edge_index >= 2;
            double delta = edge_index % 2 ? 6. : -6.;
            GtkAdjustment *hadj = gtk_scrolled_window_get_hadjustment (GTK_SCROLLED_WINDOW (scroller));
            GtkAdjustment *vadj = gtk_scrolled_window_get_vadjustment (GTK_SCROLLED_WINDOW (scroller));
            gtk_adjustment_set_value (hadj, gtk_adjustment_get_lower (hadj));
            gtk_adjustment_set_value (vadj, gtk_adjustment_get_lower (vadj));
            GtkAdjustment *adj = horizontal ? hadj : vadj;
            double edge = delta < 0 ? gtk_adjustment_get_lower (adj) :
                          gtk_adjustment_get_upper (adj) - gtk_adjustment_get_page_size (adj);
            gtk_adjustment_set_value (adj, edge);
            settle (.08);
            g_assert_true (gtk_adjustment_get_upper (adj) > gtk_adjustment_get_page_size (adj));
            point (child, window, &bx, &by);
            gint bar_x[2], bar_y[2];
            for (gint b = 0; b < 2; b++)
              point (bars[b], window, &bar_x[b], &bar_y[b]);
            GdkEvent *event = gdk_event_new (GDK_SCROLL);
            event->scroll.window = g_object_ref (gtk_widget_get_window (scroller));
            event->scroll.send_event = TRUE;
            event->scroll.time = GDK_CURRENT_TIME;
            event->scroll.x = event->scroll.y = 100;
            event->scroll.direction = GDK_SCROLL_SMOOTH;
            event->scroll.delta_x = horizontal ? delta : 0.;
            event->scroll.delta_y = horizontal ? 0. : delta;
            GdkDevice *pointer = gdk_seat_get_pointer (gdk_display_get_default_seat (gdk_display_get_default ()));
            gdk_event_set_device (event, pointer);
            gdk_event_set_source_device (event, pointer);
            g_assert_true (gtk_widget_event (scroller, event));
            gdk_event_free (event);
            gint ax, ay;
            point (child, window, &ax, &ay);
            gint displacement = horizontal ? ax - bx : ay - by;
            if (stock)
              g_assert_cmpint (displacement, ==, 0);
            else
              {
                g_assert_cmpint (ABS (displacement), >, 3);
                g_assert_cmpint (ABS (displacement), <, 240);
                g_assert_true (displacement * delta < 0);
              }
            g_assert_true (fabs (gtk_adjustment_get_value (adj) - edge) < .01);
            for (gint b = 0; b < 2; b++)
              {
                gint x, y;
                point (bars[b], window, &x, &y);
                g_assert_cmpint (x, ==, bar_x[b]);
                g_assert_cmpint (y, ==, bar_y[b]);
              }
            if (kind == 2 && delta < 0 && !stock)
              {
                cairo_surface_t *surface = cairo_image_surface_create (CAIRO_FORMAT_ARGB32, gtk_widget_get_allocated_width (window), gtk_widget_get_allocated_height (window));
                cairo_t *cr = cairo_create (surface);
                gtk_widget_draw (window, cr);
                g_assert_false (red_pixel (surface, bx + 4, by + 4));
                g_assert_true (red_pixel (surface, ax + 8, ay + 8));
                cairo_destroy (cr);
                cairo_surface_destroy (surface);
              }
            settle (1.15);
            point (child, window, &ax, &ay);
            g_assert_cmpint (ax, ==, bx);
            g_assert_cmpint (ay, ==, by);
            count++;
            g_print ("PASS: kind=%d overlay=%d axis=%c delta=%g displacement=%d\n", kind, overlay, horizontal ? 'x' : 'y', delta, displacement);
          }
        gtk_widget_hide (window);
        gtk_widget_unrealize (window);
        gtk_widget_show_all (window);
        settle (.08);
        gint x, y;
        point (child, window, &x, &y);
        g_assert_cmpint (x, ==, bx);
        g_assert_cmpint (y, ==, by);
        gtk_widget_destroy (window);
        settle (.02);
      }
  g_print ("PASS: %d %s C scroll cases and window lifecycle; pointer size %zu\n", count, stock ? "stock" : "patched", sizeof (void *));
  return 0;
}
