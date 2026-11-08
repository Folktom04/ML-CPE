import { fireEvent, render, screen } from '@testing-library/react-native';
import { Linking } from 'react-native';

import { ProductsCard } from '@/components/ProductsCard';
import {
  peakAlertUvi,
  PRODUCT_LINKS,
  PRODUCTS,
  productUrl,
  recommendProducts,
  searchUrl,
} from '@/lib/products';

import { mkHours } from './fixtures';

const START = '2026-11-08T06:00:00+07:00';
const keys = (peak: number) => recommendProducts(peak).map((p) => p.key);

describe('products', () => {
  it('peak uses alert_uvi of daylight hours only', () => {
    const hours = mkHours(START, [2, 9, 4, 12], [true, true, true, false]);
    expect(peakAlertUvi(hours)).toBe(9);
    expect(peakAlertUvi([])).toBe(0);
  });

  it('picks products by the WHO level of the peak (x.5 rounds up)', () => {
    expect(keys(2.4)).toEqual(['spf30', 'hat']);
    expect(keys(2.5)).toEqual(['spf30', 'water', 'hat', 'glasses', 'umbrella', 'shirt']);
    expect(keys(5.5)[0]).toBe('spf50');
    expect(keys(9)).toHaveLength(6);
  });

  it('search links per store, replaced by a specific link when set', () => {
    const spf50 = PRODUCTS.find((p) => p.key === 'spf50')!;
    expect(productUrl(spf50, 'shopee')).toBe(searchUrl('shopee', spf50.keyword));
    expect(searchUrl('shopee', 'a b')).toBe('https://shopee.co.th/search?keyword=a%20b');
    expect(searchUrl('lazada', 'a b')).toBe('https://www.lazada.co.th/catalog/?q=a%20b');
    PRODUCT_LINKS.spf50 = { lazada: 'https://www.lazada.co.th/products/x.html' };
    try {
      expect(productUrl(spf50, 'lazada')).toBe('https://www.lazada.co.th/products/x.html');
      expect(productUrl(spf50, 'shopee')).toBe(searchUrl('shopee', spf50.keyword));
    } finally {
      delete PRODUCT_LINKS.spf50;
    }
  });
});

describe('ProductsCard', () => {
  const hours = mkHours(START, [3, 6, 9, 0], [true, true, true, false]);

  it('tapping a picture shows the stores, a store opens its link', async () => {
    const open = jest.spyOn(Linking, 'openURL').mockResolvedValue(true);
    await render(<ProductsCard hours={hours} />);
    expect(screen.getByTestId('products-reason')).toHaveTextContent(/9\.0 \(สูงมาก\)/);
    expect(screen.queryByTestId('product-stores-spf50')).toBeNull();
    await fireEvent.press(screen.getByTestId('product-image-spf50'));
    expect(screen.getByTestId('product-stores-spf50')).toBeTruthy();
    await fireEvent.press(screen.getByTestId('product-spf50-shopee'));
    expect(open).toHaveBeenCalledWith(searchUrl('shopee', 'ครีมกันแดด SPF50 PA++++'));
    // tapping the picture again closes the choice
    await fireEvent.press(screen.getByTestId('product-image-spf50'));
    expect(screen.queryByTestId('product-stores-spf50')).toBeNull();
    open.mockRestore();
  });

  it('shows a message when the store cannot be opened', async () => {
    const open = jest.spyOn(Linking, 'openURL').mockRejectedValue(new Error('no app'));
    await render(<ProductsCard hours={hours} />);
    await fireEvent.press(screen.getByTestId('product-image-hat'));
    await fireEvent.press(screen.getByTestId('product-hat-lazada'));
    expect(await screen.findByTestId('products-error')).toBeTruthy();
    open.mockRestore();
  });
});
