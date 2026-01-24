// src/App.test.jsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import App from './App';

describe('App', () => {
  it('renders the main application title', () => {
    // Render the App component
    render(&lt;App /&gt;);

    // Use screen.getByText to find an element with the specified text content.
    // The 'i' flag makes the match case-insensitive.
    const titleElement = screen.getByText(/Plataforma de Otimização de Arruamento/i);

    // Assert that the element is in the document
    expect(titleElement).toBeInTheDocument();
  });
});
