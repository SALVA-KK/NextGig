import React from 'react';
import Navbar from '../components/home/Navbar';
import Hero from '../components/home/Hero';
import Features from '../components/home/Features';
import CTA from '../components/home/CTA';
import Footer from '../components/home/Footer';

export default function Home() {
  return (
    <div className="home-page">
      <Navbar />
      <main className="home-main-content">
        <Hero />
        <Features />
        <CTA />
      </main>
      <Footer />
    </div>
  );
}
